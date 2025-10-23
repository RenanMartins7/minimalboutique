FROM python:3.11-slim

WORKDIR /app

# Copia apenas o código do serviço de payment
COPY ./payment /app

# Instala as dependências (assumindo que 'requirements.txt' será atualizado)
RUN pip install --no-cache-dir -r requirements.txt

# Comando CMD modificado para rodar Uvicorn com FastAPI
# (Usando porta 8004 como exemplo para o payment-service)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5004", "--workers", "4"]
