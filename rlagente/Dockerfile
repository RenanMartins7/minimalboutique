FROM python:3.12-slim

RUN pip install kubernetes pyyaml "elasticsearch>=8.6.0,<9.0.0"

WORKDIR /app
COPY . .

CMD ["python", "manager.py"]