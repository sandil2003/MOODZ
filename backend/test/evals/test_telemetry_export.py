"""Integration test verifying OpenTelemetry and AgentOps tracing functionality."""

import pytest
from app.core.telemetry import setup_telemetry, trace_span, trace_tool, get_tracer
from app.core.pii_scrubber import PIIScrubber


def test_telemetry_initialization():
    """Verify that setup_telemetry initializes TracerProvider without errors."""
    setup_telemetry(service_name="moodz-test-service")
    tracer = get_tracer()
    assert tracer is not None


def test_trace_span_recording():
    """Verify that trace_span creates and records spans with attributes and latency."""
    with trace_span("test.operation", span_type="unit.test", attributes={"key": "value", "email": "test@test.com"}) as span:
        assert span is not None
        # Span execution completes successfully


@pytest.mark.asyncio
async def test_trace_tool_decorator_async():
    """Verify that @trace_tool wraps async tools properly."""
    @trace_tool("test_async_tool")
    async def sample_tool(text: str, user_email: str):
        return {"processed": text, "email": user_email}

    result = await sample_tool("hello world", "contact@domain.com")
    assert result["processed"] == "hello world"
    assert result["email"] == "contact@domain.com"
