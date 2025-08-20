import os
from flask import Flask
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor


def configure_telemetry(app: Flask, service_name: str):
    resource = Resource(attributes={"service.name": service_name, "service.instance.id": os.uname().nodename,})
    trace.set_tracer_provider(TracerProvider(resource=resource))
    tracer_provider = trace.get_tracer_provider()

    exporter = OTLPSpanExporter(endpoint="http://collector:4321/v1/traces")

    span_processor = BatchSpanProcessor(exporter)
    tracer_provider.add_span_processor(span_processor)

    FlaskInstrumentor().instrument_app(app)

    RequestsInstrumentor().instrument()

    # from database import db 

    # SQLAlchemyInstrumentor().instrument(engine=db.engine)

    print(f"Opentelemetry configurado com sucesso para o serviço: {service_name}")

