FROM python:3.11-slim

WORKDIR /app

# Copia apenas o código do serviço de carrinho
COPY ./cart /app

# Instala as dependências (assumindo que 'requirements.txt' será atualizado)
RUN pip install --no-cache-dir -r requirements.txt

# Comando CMD modificado para rodar Uvicorn com FastAPI
# (Usando porta 8002 como exemplo para o cart-service)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5005", "--workers", "4"]
