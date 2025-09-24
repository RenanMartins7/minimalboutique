from elasticsearch import Elasticsearch
import json
import os
import math
from collections import Counter
import hashlib

# 🔹 Usa o serviço "elasticsearch" do Kubernetes por padrão
ES_HOST = os.getenv("ES_HOST", "http://elasticsearch:9200")
ES_INDEX = os.getenv("ES_INDEX", "jaeger-span-*")

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

def trace_to_string(spans, use_hash=True):
    """
    Constrói uma representação determinística de um trace a partir de sua lista de spans.
    Se use_hash=True, retorna um hash SHA256 curto.
    """
    spans_repr = []
    for span in sorted(spans, key=lambda s: (s.get("startTime", 0), s.get("spanID", ""))):
        span_repr = {
            "operationName": span.get("operationName"),
            "serviceName": span.get("process", {}).get("serviceName"),
            "tags": {
                tag["key"]: str(tag["value"])
                for tag in sorted(span.get("tags", []), key=lambda t: t["key"])
            }
        }
        spans_repr.append(span_repr)

    # String JSON determinística
    canonical = json.dumps(spans_repr, sort_keys=True, separators=(",", ":"))

    if use_hash:
        # Retorna só o hash SHA256 (mais compacto e eficiente p/ entropia)
        return hashlib.sha256(canonical.encode()).hexdigest()
    else:
        return canonical


def calcular_entropia(traces):
    """
    Calcula a entropia Shannon a partir das strings representando cada trace.
    """
    strings = []
    for trace_id, spans in traces.items():
        s = trace_to_string(spans)  # agora spans é a lista já organizada
        strings.append(s)

    if not strings:
        return 0.0

    counter = Counter(strings)
    total = sum(counter.values())

    entropia = 0.0
    for freq in counter.values():
        p = freq / total
        entropia -= p * math.log2(p)

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

    # 🔹 Calcula e retorna a entropia diretamente
    return traces


def export_traces_by_hash(config_hash):
    """
    Função principal: busca spans de um hash, monta os traces e retorna a entropia.
    """
    spans = get_spans_by_hash(config_hash)
    traces = group_spans_by_trace(spans)

    return calcular_entropia(traces), len(traces)
