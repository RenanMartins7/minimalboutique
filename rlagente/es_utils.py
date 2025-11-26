from elasticsearch import Elasticsearch
import json
import os
import math
from collections import Counter
import hashlib

# 🔹 Usa o serviço "elasticsearch" do Kubernetes por padrão
ES_HOST = os.getenv("ES_HOST", "http://elasticsearch:9200")
ES_INDEX = os.getenv("ES_INDEX", "jaeger-span-*")

# 🔧 Parâmetros de entropia e quantização (via ENV, sem mudar assinaturas)
def _env_float(name, default):
    try:
        return float(os.getenv(name, default))
    except Exception:
        return default

def _env_int(name, default):
    try:
        return int(os.getenv(name, default))
    except Exception:
        return default

ENTROPY_ALPHA = _env_float("ENTROPY_ALPHA", 1.0)  # α>1 => mais punitivo para repetidos
QUANTIZE_MS = _env_int("QUANTIZE_MS", 200)         # bucketização de durações/latências
QUANTIZE_KEYS = set(
    [s.strip() for s in os.getenv("QUANTIZE_KEYS", "duration_ms,latency_ms,http.duration_ms,db.duration_ms").split(",") if s.strip()]
)

# Cria cliente Elasticsearch
es = Elasticsearch([ES_HOST])


def get_spans_by_hash(config_hash, scroll_size=5000):
    query = {
        "query": {
            "nested": {
                "path": "tags",
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"tags.key": "experiment_hash"}},
                            {"term": {"tags.value": config_hash}}
                        ]
                    }
                }
            }
        }
    }
    resp = es.search(index=ES_INDEX, body=query, size=scroll_size, scroll="2m")

    spans = []
    sid = resp["_scroll_id"]
    scroll_size = len(resp["hits"]["hits"])

    while scroll_size > 0:
        for hit in resp["hits"]["hits"]:
            spans.append(hit["_source"])

        resp = es.scroll(scroll_id=sid, scroll="2m")
        sid = resp["_scroll_id"]
        scroll_size = len(resp["hits"]["hits"])

    #print(f"Total de spans encontrados para hash {config_hash}: {len(spans)}")
    return spans


def _is_number(x):
    if isinstance(x, (int, float)):
        return True
    if isinstance(x, str):
        try:
            float(x)
            return True
        except Exception:
            return False
    return False

def _to_float(x):
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(str(x))
    except Exception:
        return None

def _quantize_value_if_applicable(key, value, bucket_ms):
    """
    Se a chave estiver em QUANTIZE_KEYS e o valor for numérico, aplica bucketização (ms).
    Retorna (string) o valor possivelmente quantizado para estabilizar padrões.
    """
    if key in QUANTIZE_KEYS and _is_number(value):
        v = _to_float(value)
        if v is not None and bucket_ms > 0:
            # arredonda para o bucket mais próximo
            bucketed = int(round(v / bucket_ms)) * bucket_ms
            return str(bucketed)
    # fallback: string
    return str(value)


def trace_to_string(spans, use_hash=True, tag_blacklist=None):
    """
    Constrói uma string determinística representando a hierarquia de um trace.
    - Cada span é um bloco: "Serviço:Operação|tag1=valor1|tag2=valor2|..."
    - A hierarquia é respeitada: pai → filhos (em ordem de startTime)
    - Tags que estão na 'tag_blacklist' são ignoradas.
    - Se use_hash=True, retorna o hash SHA256 da string final.

    🔧 Modificações:
    - Quantização de tags numéricas em QUANTIZE_KEYS por buckets de QUANTIZE_MS (via ENV).
    """
    if tag_blacklist is None:
        tag_blacklist = {
            "otel.status_code",
            "span.kind",
            "thread.id",
            "thread.name",
            "http.status_code",
            "peer.ipv4",
            "peer.ipv6",
            "peer.port",
            "peer.service",
            "pid",
            "telemetry.sdk.language",
            "telemetry.sdk.name",
            "telemetry.sdk.version",
            "net.peer.port",
            "user.id",
            "order.id"
        }

    # Mapeia spans por ID e constrói estrutura pai → filhos
    spans_by_id = {s['spanID']: s for s in spans}
    children_map = {s['spanID']: [] for s in spans}
    root_spans = []

    for span in spans:
        parent_id = None
        references = span.get("references", [])
        for ref in references:
            if ref.get("refType") == "CHILD_OF":
                parent_id = ref.get("spanID")
                break

        if parent_id and parent_id in spans_by_id:
            children_map[parent_id].append(span)
        else:
            root_spans.append(span)

    # Ordena spans raiz
    root_spans.sort(key=lambda s: s.get("startTime", 0))

    def build_span_block(span, level=0):
        """
        Constrói recursivamente um bloco de texto para um span e seus filhos.
        """
        indent = "  " * level  # apenas para visualização/estabilidade
        service = span.get("process", {}).get("serviceName", "unknown")
        operation = span.get("operationName", "unknown")

        # Filtra, quantiza (quando aplicável) e ordena tags
        tags = []
        for tag in sorted(span.get("tags", []), key=lambda t: t["key"]):
            k = tag["key"]
            if k in tag_blacklist:
                continue
            v = tag.get("value")
            v_str = _quantize_value_if_applicable(k, v, QUANTIZE_MS)
            tags.append(f"{k}={v_str}")

        # Monta o bloco do span
        span_str = f"{indent}{service}:{operation}"
        if tags:
            span_str += "|" + "|".join(tags)

        # Concatena recursivamente os filhos
        children = sorted(children_map.get(span["spanID"], []), key=lambda s: s.get("startTime", 0))
        for child in children:
            span_str += "\n" + build_span_block(child, level + 1)

        return span_str

    # Constrói a string completa (ordem determinística dos spans raiz)
    full_str_parts = []
    for root in root_spans:
        full_str_parts.append(build_span_block(root))

    canonical_str = "\n".join(full_str_parts)

    # Retorna o hash se desejado
    if use_hash:
        return hashlib.sha256(canonical_str.encode()).hexdigest()
    else:
        return canonical_str


def calcular_entropia(traces):
    """
    Calcula a entropia (por padrão, Rényi com α=ENTROPY_ALPHA) a partir das strings representando cada trace.
    - Se ENTROPY_ALPHA == 1.0 => Shannon (compatível conceitualmente).
    - Mantém a mesma assinatura e retorna um float como antes.
    """
    strings = []
    for trace_id, spans in traces.items():
        s = trace_to_string(spans)  # spans já organizados; aplica quantização na serialização
        strings.append(s)

    if not strings:
        return 0.0

    counter = Counter(strings)
    total = sum(counter.values())
    ps = [c / total for c in counter.values()]

    alpha = ENTROPY_ALPHA

    # Shannon (base 2) se α=1
    if abs(alpha - 1.0) < 1e-12:
        entropia = -sum(p * math.log2(p) for p in ps if p > 0)
        return entropia

    # Rényi geral (base 2): H_α = (1/(1-α)) * log2(Σ p_i^α)
    # α>1 penaliza fortemente duplicatas
    sum_p_alpha = sum((p ** alpha) for p in ps)
    # Evita problemas numéricos
    sum_p_alpha = max(sum_p_alpha, 1e-300)
    entropia = (1.0 / (1.0 - alpha)) * math.log2(sum_p_alpha)
    return entropia


def group_spans_by_trace(spans):
    """
    Agrupa spans pelo traceId e ordena cada trace hierarquicamente (pais antes dos filhos),
    lendo a referência de parentesco da lista 'references'.
    Spans no mesmo nível são ordenados pelo horário de início.
    """
    traces = {}

    # 1. Agrupa spans por traceID
    for span in spans:
        trace_id = span.get("traceID")
        if not trace_id:
            continue
        if trace_id not in traces:
            traces[trace_id] = []
        traces[trace_id].append(span)

    # 2. Ordena os spans de cada trace hierarquicamente
    for trace_id, trace_spans in traces.items():
        spans_by_id = {s['spanID']: s for s in trace_spans}
        children_map = {s['spanID']: [] for s in trace_spans}
        root_spans = []

        # Constrói a árvore de dependências (pais e filhos)
        for span in trace_spans:
            parent_id = None
            references = span.get("references", [])
            if references:
                for ref in references:
                    if ref.get("refType") == "CHILD_OF":
                        parent_id = ref.get("spanID")
                        break

            if parent_id and parent_id in spans_by_id:
                children_map[parent_id].append(span)
            else:
                root_spans.append(span)

        # Ordena os spans raiz pelo tempo de início
        root_spans.sort(key=lambda s: s.get("startTime", 0))

        sorted_trace = []

        def traverse(span):
            sorted_trace.append(span)
            children = children_map.get(span['spanID'], [])
            children.sort(key=lambda s: s.get("startTime", 0))
            for child in children:
                traverse(child)

        for root in root_spans:
            traverse(root)

        traces[trace_id] = sorted_trace

    #print(f"Total de traces agrupados: {len(traces)}")

    # 🔹 Retorna os traces (entropia calculada separadamente)
    return traces


def export_traces_by_hash(config_hash):
    """
    Função principal: busca spans de um hash, monta os traces e retorna a entropia.
    Retorna (entropia, quantidade_de_traces) — mesmas saídas de antes.
    """
    spans = get_spans_by_hash(config_hash)
    traces = group_spans_by_trace(spans)

    return calcular_entropia(traces), len(traces)
