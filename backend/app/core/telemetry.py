"""AgentOps Telemetry & OpenTelemetry Tracing Module for MOODZ.

Provides:
- OpenTelemetry TracerProvider initialization with Arize Phoenix (OTLP) support
- Auto-instrumentation of LangChain / LangGraph and FastAPI
- Context managers and decorators for tracing tool calls and state nodes
- Automated PII scrubbing on all recorded span attributes
- Graceful no-op fallback when OpenTelemetry collector or SDK is not available
"""

import os
import time
import socket
import logging
import inspect
from typing import Optional, Dict, Any, Callable
from urllib.parse import urlparse
from functools import wraps
from contextlib import contextmanager

from app.core.pii_scrubber import PIIScrubber

logger = logging.getLogger(__name__)

# Standard model pricing benchmarks ($ per 1 Million Tokens)
MODEL_PRICING: Dict[str, tuple[float, float]] = {
    "gemini-2.5-flash": (0.075, 0.30),
    "gemini-1.5-flash": (0.075, 0.30),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-1.5-pro": (1.25, 5.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
}


def record_llm_metrics(
    span: Any,
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0
) -> Dict[str, Any]:
    """Calculate and record token consumption and estimated dollar costs on a trace span."""
    in_rate, out_rate = MODEL_PRICING.get(model, (0.10, 0.40))
    cost_usd = ((input_tokens / 1_000_000.0) * in_rate) + ((output_tokens / 1_000_000.0) * out_rate)

    metrics = {
        "llm.model": model,
        "llm.input_tokens": input_tokens,
        "llm.output_tokens": output_tokens,
        "llm.total_tokens": input_tokens + output_tokens,
        "llm.estimated_cost_usd": round(cost_usd, 7)
    }

    if span is not None and hasattr(span, "set_attribute"):
        for k, v in metrics.items():
            span.set_attribute(k, v)

    return metrics


def _is_collector_reachable(endpoint: str) -> bool:
    """Check if the OTLP collector gRPC port is reachable before registering BatchSpanProcessor."""
    try:
        if "://" in endpoint:
            parsed = urlparse(endpoint)
            host = parsed.hostname or "localhost"
            port = parsed.port or 4317
        else:
            parts = endpoint.split(":")
            host = parts[0]
            port = int(parts[1]) if len(parts) > 1 else 4317
        with socket.create_connection((host, port), timeout=0.25):
            return True
    except Exception:
        return False


# Attempt to import OpenTelemetry components safely
_HAS_OTEL = False
try:
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    _HAS_OTEL = True
except Exception as _otel_err:
    logger.debug(f"[AgentOps] Note: OpenTelemetry SDK not fully loaded ({_otel_err}). Operating with lightweight tracer.")


class _DummySpan:
    """No-op span when OpenTelemetry is unavailable."""
    def __init__(self, name: str):
        self.name = name
        self.attributes: Dict[str, Any] = {}

    def set_attribute(self, key: str, value: Any):
        self.attributes[key] = value

    def set_status(self, status: Any):
        pass

    def record_exception(self, exception: Exception):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class _DummyTracer:
    """No-op tracer providing standard span context."""
    def start_as_current_span(self, name: str):
        return _DummySpan(name)


_IS_INITIALIZED = False
_TRACER: Any = None


def setup_telemetry(
    service_name: str = "moodz-ai-agent",
    endpoint: Optional[str] = None,
    app: Optional[Any] = None
) -> None:
    """Initialize OpenTelemetry tracer provider with OTLP exporter and auto-instrumentations."""
    global _IS_INITIALIZED, _TRACER

    if _IS_INITIALIZED:
        if app is not None:
            try:
                from openinference.instrumentation.fastapi import FastAPIInstrumentor
                FastAPIInstrumentor().instrument_app(app)
            except Exception:
                pass
        return

    collector_endpoint = endpoint or os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:4317")

    if _HAS_OTEL:
        try:
            resource = Resource.create({
                "service.name": service_name,
                "service.version": "1.0.0",
                "deployment.environment": os.getenv("ENVIRONMENT", "development")
            })

            provider = TracerProvider(resource=resource)

            if _is_collector_reachable(collector_endpoint):
                try:
                    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
                    exporter = OTLPSpanExporter(endpoint=collector_endpoint, insecure=True)
                    processor = BatchSpanProcessor(exporter)
                    provider.add_span_processor(processor)
                    logger.info(f"[AgentOps] OTLP exporter configured for endpoint: {collector_endpoint}")
                except Exception as e:
                    logger.debug(f"[AgentOps] OTLP exporter setup note: {e}")
            else:
                logger.info(f"[AgentOps] OTLP collector not active at {collector_endpoint}. Using in-memory tracer.")

            trace.set_tracer_provider(provider)
            _TRACER = trace.get_tracer(service_name)

            try:
                from openinference.instrumentation.langchain import LangChainInstrumentor
                LangChainInstrumentor().instrument()
            except Exception as e:
                logger.debug(f"[AgentOps] OpenInference LangChain instrumentor note: {e}")

            if app is not None:
                try:
                    from openinference.instrumentation.fastapi import FastAPIInstrumentor
                    FastAPIInstrumentor().instrument_app(app)
                except Exception as e:
                    logger.debug(f"[AgentOps] OpenInference FastAPI instrumentor note: {e}")

            _IS_INITIALIZED = True
            return
        except Exception as e:
            logger.warning(f"[AgentOps] Warning configuring OpenTelemetry ({e}). Falling back to local tracer.")

    _TRACER = _DummyTracer()
    _IS_INITIALIZED = True


def get_tracer():
    """Retrieve the global tracer instance."""
    global _TRACER
    if _TRACER is None:
        if _HAS_OTEL:
            try:
                _TRACER = trace.get_tracer("moodz-ai-agent")
            except Exception:
                _TRACER = _DummyTracer()
        else:
            _TRACER = _DummyTracer()
    return _TRACER


@contextmanager
def trace_span(
    name: str,
    span_type: str = "agent.step",
    attributes: Optional[Dict[str, Any]] = None
):
    """Context manager to trace an execution block with automatic timing and PII scrubbing."""
    tracer = get_tracer()
    start_time = time.perf_counter()

    with tracer.start_as_current_span(name) as span:
        span.set_attribute("span.type", span_type)

        if attributes:
            clean_attrs = PIIScrubber.scrub_dict(attributes)
            for k, v in clean_attrs.items():
                val = v if isinstance(v, (str, bool, int, float)) else str(v)
                span.set_attribute(f"moodz.{k}", val)

        try:
            yield span
            if _HAS_OTEL and hasattr(span, "set_status"):
                span.set_status(Status(StatusCode.OK))
        except Exception as exc:
            if hasattr(span, "record_exception"):
                span.record_exception(exc)
            if _HAS_OTEL and hasattr(span, "set_status"):
                span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise
        finally:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            span.set_attribute("moodz.latency_ms", elapsed_ms)


def trace_tool(tool_name: str):
    """Decorator to automatically trace Google ADK or LangGraph tool calls with timing and PII scrubbing."""
    def decorator(func: Callable):
        def _record_tool_start(span, kwargs):
            span.set_attribute("tool.name", tool_name)
            scrubbed_args = PIIScrubber.scrub_dict(kwargs)
            for k, v in scrubbed_args.items():
                span.set_attribute(f"tool.arg.{k}", str(v)[:200])

        def _record_tool_success(span, start_time):
            if _HAS_OTEL and hasattr(span, "set_status"):
                span.set_status(Status(StatusCode.OK))
            span.set_attribute("tool.success", True)
            duration_ms = (time.perf_counter() - start_time) * 1000
            span.set_attribute("tool.duration_ms", duration_ms)

        def _record_tool_error(span, start_time, error):
            if hasattr(span, "record_exception"):
                span.record_exception(error)
            if _HAS_OTEL and hasattr(span, "set_status"):
                span.set_status(Status(StatusCode.ERROR, str(error)))
            span.set_attribute("tool.success", False)
            duration_ms = (time.perf_counter() - start_time) * 1000
            span.set_attribute("tool.duration_ms", duration_ms)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_as_current_span(f"tool.{tool_name}") as span:
                _record_tool_start(span, kwargs)
                start_t = time.perf_counter()
                try:
                    result = await func(*args, **kwargs)
                    _record_tool_success(span, start_t)
                    return result
                except Exception as e:
                    _record_tool_error(span, start_t, e)
                    raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_as_current_span(f"tool.{tool_name}") as span:
                _record_tool_start(span, kwargs)
                start_t = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    _record_tool_success(span, start_t)
                    return result
                except Exception as e:
                    _record_tool_error(span, start_t, e)
                    raise

        return async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper

    return decorator
