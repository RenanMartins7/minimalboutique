FROM python:3.11-slim
WORKDIR /loadgen

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY locustfile.py .

ENTRYPOINT ["locust", "--host", "http://backend:5000", "--headless", "-u", "100", "-r", "10"]