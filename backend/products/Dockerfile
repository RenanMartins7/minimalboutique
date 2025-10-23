FROM python:3.11-slim

WORKDIR /app

# Copia apenas o código do serviço 'products'
COPY ./products /app

# Instala as dependências (assumindo 'requirements.txt' será atualizado)
RUN pip install --no-cache-dir -r requirements.txt

# Comando CMD modificado para rodar Uvicorn com FastAPI na porta 5001
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5001", "--workers", "4"]