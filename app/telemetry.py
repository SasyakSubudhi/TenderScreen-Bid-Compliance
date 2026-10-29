"""Shared tracing configuration and queue propagation helpers."""
import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.propagate import inject,extract
from prometheus_client import Histogram,Counter
STEP_LATENCY=Histogram('agent_step_seconds','Recorded agent step latency',['agent','step'],buckets=(.001,.01,.1,.5,1,2,5,10,20,45))
TOKENS=Counter('agent_tokens_total','Provider reported tokens',['agent','kind'])
COST=Counter('agent_cost_usd_total','Known provider charge USD',['agent'])
provider=TracerProvider(resource=Resource.create({'service.name':os.getenv('WORKER_ROLE',os.getenv('SERVICE_NAME','api'))}))
if os.getenv('OTEL_EXPORTER_OTLP_TRACES_ENDPOINT'):
 provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(provider)
tracer=trace.get_tracer('tenderscreen')
def carrier():
 result={};inject(result);return result
