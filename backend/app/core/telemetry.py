"""AgentOps Telemetry & OpenTelemetry Tracing Module for MOODZ.

Provides:
- OpenTelemetry TracerProvider initialization with OTLP / Arize Phoenix support
- Auto-instrumentation of LangChain / LangGraph execution
- Context manager / decorator for tracing Google ADK tools and state nodes
- Automated PII scrubbing on all recorded span attributes
- Graceful no-op fallback when OpenTelemetry SDK dependencies are mismatched or missing
"""

import os
import time
from typing import Optional, Dict, Any, Callable
from functools import wraps
from contextlib import contextmanager
from app.core.pii_scrubber import PIIScrubber

# Attempt to import OpenTelemetry components safely
_HAS_OTEL = False
try:
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode, Span
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    _HAS_OTEL = True
except Exception as _otel_err:
    print(f"[AgentOps] Note: OpenTelemetry SDK not fully loaded ({_otel_err}). Operating with lightweight tracer.")


# Fallback / Lightweight Tracer for resilience
class _DummySpan:
    """No-op span when OpenTelemetry is unavailable."""
    def __init__(self, name: str):
        self.name = name
        self.attributes = {}

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
    endpoint: Optional[str] = None
) -> None:
    """Initialize OpenTelemetry tracer provider with OTLP exporter and auto-instrumentations."""
    global _IS_INITIALIZED, _TRACER

    if _IS_INITIALIZED:
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

            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
                exporter = OTLPSpanExporter(endpoint=collector_endpoint, insecure=True)
                processor = BatchSpanProcessor(exporter)
                provider.add_span_processor(processor)
                print(f"[AgentOps] OTLP exporter configured for endpoint: {collector_endpoint}")
            except Exception as e:
                print(f"[AgentOps] Info: OTLP exporter unavailable ({e}). Using local tracer.")

            trace.set_tracer_provider(provider)
            _TRACER = trace.get_tracer(service_name)

            try:
                from openinference.instrumentation.langchain import LangChainInstrumentor
                LangChainInstrumentor().instrument()
                print("[AgentOps] OpenInference LangChain instrumentor initialized successfully")
            except Exception as e:
                print(f"[AgentOps] OpenInference LangChain instrumentor note: {e}")

            _IS_INITIALIZED = True
            print(f"[AgentOps] Telemetry active for service '{service_name}'")
            return
        except Exception as e:
            print(f"[AgentOps] Warning configuring OpenTelemetry ({e}). Falling back to local tracer.")

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
                if isinstance(v, (str, bool, int, float)):
                    span.set_attribute(f"moodz.{k}", v)
                else:
                    span.set_attribute(f"moodz.{k}", str(v))

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
    """Decorator to automatically trace Google ADK or LangGraph tool calls."""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_as_current_span(f"tool.{tool_name}") as span:
                span.set_attribute("tool.name", tool_name)
                scrubbed_args = PIIScrubber.scrub_dict(kwargs)
                for k, v in scrubbed_args.items():
                    span.set_attribute(f"tool.arg.{k}", str(v)[:200])

                start_t = time.perf_counter()
                try:
                    result = await func(*args, **kwargs)
                    if _HAS_OTEL and hasattr(span, "set_status"):
                        span.set_status(Status(StatusCode.OK))
                    span.set_attribute("tool.success", True)
                    return result
                except Exception as e:
                    if hasattr(span, "record_exception"):
                        span.record_exception(e)
                    if _HAS_OTEL and hasattr(span, "set_status"):
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.set_attribute("tool.success", False)
                    raise
                finally:
                    duration_ms = (time.perf_counter() - start_t) * 1000
                    span.set_attribute("tool.duration_ms", duration_ms)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_as_current_span(f"tool.{tool_name}") as span:
                span.set_attribute("tool.name", tool_name)
                scrubbed_args = PIIScrubber.scrub_dict(kwargs)
                for k, v in scrubbed_args.items():
                    span.set_attribute(f"tool.arg.{k}", str(v)[:200])

                start_t = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    if _HAS_OTEL and hasattr(span, "set_status"):
                        span.set_status(Status(StatusCode.OK))
                    span.set_attribute("tool.success", True)
                    return result
                except Exception as e:
                    if hasattr(span, "record_exception"):
                        span.record_exception(e)
                    if _HAS_OTEL and hasattr(span, "set_status"):
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.set_attribute("tool.success", False)
                    raise
                finally:
                    duration_ms = (time.perf_counter() - start_t) * 1000
                    span.set_attribute("tool.duration_ms", duration_ms)

        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator
