import requests
import json

# URL do Elasticsearch (ajuste se precisar)
url = "http://elasticsearch:9200/jaeger-span-*/_search?size=10000"

# Faz a requisição
resp = requests.get(url)
resp.raise_for_status()

# Converte para JSON
data = resp.json()

# Salva em arquivo
with open("dados.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("✅ Dados salvos em dados.json")
