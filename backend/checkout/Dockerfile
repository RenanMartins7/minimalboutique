FROM python:3.11-slim

WORKDIR /app

# Copia apenas o código do serviço de checkout
COPY ./checkout /app

# Instala as dependências (assumindo que 'requirements.txt' será atualizado)
RUN pip install --no-cache-dir -r requirements.txt

# Comando CMD modificado para rodar Uvicorn com FastAPI
# (Usando porta 8003 como exemplo para o checkout-service)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5003", "--workers", "4"]