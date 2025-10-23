#!/bin/sh

# Espera 30 segundos
echo "Aguardando 30 segundos antes de iniciar o Gunicorn..."
sleep 30

# Executa o Gunicorn com variáveis de ambiente para workers e threads
exec gunicorn -w ${WORKERS:-4} -k gthread --threads ${THREADS:-8} -b 0.0.0.0:5001 app:app
