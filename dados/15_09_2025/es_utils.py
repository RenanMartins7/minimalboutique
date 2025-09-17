from elasticsearch import Elasticsearch
import json
import os

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

    print(f"Total de spans encontrados para hash {config_hash}: {len(spans)}")
    return spans


def group_spans_by_trace(spans):
    """
    Agrupa spans pelo traceId e ordena cada trace por startTimeUnixNano.
    """
    traces = {}

    for span in spans:
        trace_id = span.get("traceID")
        if not trace_id:
            continue

        if trace_id not in traces:
            traces[trace_id] = []

        traces[trace_id].append(span)

    # Ordena spans dentro de cada trace
    for trace_id in traces:
        traces[trace_id].sort(key=lambda s: s.get("startTimeUnixNano", 0))

    print(f"Total de traces agrupados: {len(traces)}")
    return traces


def export_traces_to_file(traces, config_hash):
    """
    Exporta os traces completos para um arquivo JSON.
    Nome do arquivo = <hash>.json
    """
    output = []

    for trace_id, spans in traces.items():
        output.append({
            "traceId": trace_id,
            "spans": spans
        })

    output_file = f"{config_hash}.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Traces exportados para {output_file}")
    return output_file


def export_traces_by_hash(config_hash):
    """
    Função principal: busca spans de um hash, monta os traces e salva em JSON.
    """
    spans = get_spans_by_hash(config_hash)
    traces = group_spans_by_trace(spans)
    return export_traces_to_file(traces, config_hash)
