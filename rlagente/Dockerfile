FROM python:3.12-slim

RUN pip install kubernetes pyyaml

WORKDIR /app
COPY manager.py .

CMD ["python", "manager.py"]