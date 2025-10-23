import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

def configure_telemetry(app: FastAPI, service_name: str, db_engine=None):
    # Define o recurso do serviço
    resource = Resource(attributes={
        "service.name": service_name,
        "service.instance.id": os.uname().nodename,
    })

    # Configura o tracer provider
    trace.set_tracer_provider(TracerProvider(resource=resource))
    tracer_provider = trace.get_tracer_provider()

    # Retry para envio de spans
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    http_session = requests.Session()
    http_session.mount("http://", adapter)
    http_session.mount("https://", adapter)

    # Exportador OTLP
    exporter = OTLPSpanExporter(
        endpoint="http://collector:4321/v1/traces",
        session=http_session
    )
    span_processor = BatchSpanProcessor(exporter)
    tracer_provider.add_span_processor(span_processor)

    # Instrumentação do FastAPI
    FastAPIInstrumentor.instrument_app(app)

    # Instrumentação do requests
    RequestsInstrumentor().instrument()

    # Instrumentação do SQLAlchemy, se engine fornecida
    if db_engine:
        SQLAlchemyInstrumentor().instrument(engine=db_engine.sync_engine)

    print(f"Opentelemetry configurado com sucesso para o serviço: {service_name}")