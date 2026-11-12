"""OpenTelemetry observability setup (Phase 5).

Configures tracing and metrics for the gateway. Traces are exported to the
``OTEL_EXPORTER_OTLP_ENDPOINT`` when set, otherwise to the console. The
FastAPI app is automatically instrumented so every request produces a span.
A ``gateway.requests`` counter and a ``gateway.agent_cost`` counter are
available for cost/observability dashboards.

All setup is best-effort: if OpenTelemetry is unavailable the app still
starts and the helpers return no-op objects.
"""

from __future__ import annotations

import os
from typing import Optional

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from opentelemetry.semconv.trace import SpanAttributes

try:  # FastAPI instrumentation (optional hard dependency once installed)
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
except Exception:  # pragma: no cover - only when otel not installed
    FastAPIInstrumentor = None  # type: ignore[assignment]


_tracer: Optional[trace.Tracer] = None
_meter: Optional[metrics.Meter] = None
_request_counter = None
_cost_counter = None


def _resource() -> Resource:
    return Resource.create(
        {
            "service.name": "governance-gateway",
            "service.version": "0.1.0",
        }
    )


def setup_observability(app) -> None:
    """Wire OpenTelemetry tracing + metrics into the FastAPI app.

    Safe to call multiple times. Degrades gracefully when exporters cannot
    be created.
    """
    global _tracer, _meter, _request_counter, _cost_counter

    # --- Tracing -------------------------------------------------------
    trace_provider = TracerProvider(resource=_resource())
    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        trace_provider.add_span_processor(
            SimpleSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
        )
    else:
        trace_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(trace_provider)
    _tracer = trace.get_tracer("gateway")

    # --- Metrics -------------------------------------------------------
    readers = []
    if otlp_endpoint:
        readers.append(PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=otlp_endpoint)))
    meter_provider = MeterProvider(resource=_resource(), metric_readers=readers)
    metrics.set_meter_provider(meter_provider)
    _meter = metrics.get_meter("gateway")
    _request_counter = _meter.create_counter(
        "gateway.requests",
        unit="1",
        description="Number of HTTP requests handled by the gateway",
    )
    _cost_counter = _meter.create_counter(
        "gateway.agent_cost",
        unit="USD",
        description="Per-agent cost incurred by tool/connector calls",
    )

    # --- FastAPI instrumentation --------------------------------------
    if FastAPIInstrumentor is not None:
        FastAPIInstrumentor().instrument_app(app)


def get_tracer() -> Optional[trace.Tracer]:
    return _tracer


def get_meter() -> Optional[metrics.Meter]:
    return _meter


def record_request(method: str, path: str, status_code: int) -> None:
    """Record an HTTP request metric (best-effort)."""
    if _request_counter is None:
        return
    _request_counter.add(
        1,
        {
            SpanAttributes.HTTP_METHOD: method,
            SpanAttributes.HTTP_ROUTE: path,
            SpanAttributes.HTTP_STATUS_CODE: status_code,
        },
    )


def record_agent_cost(
    agent_id: str,
    cost_type: str,
    amount: float,
    currency: str = "USD",
) -> None:
    """Record a per-agent cost metric (best-effort)."""
    if _cost_counter is None:
        return
    _cost_counter.add(
        amount,
        {
            "agent.id": agent_id,
            "cost.type": cost_type,
            "currency": currency,
        },
    )


def start_span(name: str, attributes: Optional[dict] = None):
    """Start a trace span (context manager). Returns a no-op span if tracing
    is not configured."""
    if _tracer is None:
        return _NoopSpan()
    return _tracer.start_span(name, attributes=attributes or {})


class _NoopSpan:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def set_attribute(self, key, value):
        return self

    def end(self):
        return None
