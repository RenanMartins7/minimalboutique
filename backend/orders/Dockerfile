FROM python:3.11-slim

WORKDIR /app

# Copia apenas o código do serviço 'orders'
COPY ./orders /app

# Instala as dependências (assumindo 'requirements.txt' será atualizado)
RUN pip install --no-cache-dir -r requirements.txt

# Comando CMD modificado para rodar Uvicorn com FastAPI
# A porta 5002 é a que os outros serviços esperam
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5002", "--workers", "4"]