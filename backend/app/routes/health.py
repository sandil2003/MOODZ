"""Health check endpoints for application readiness, database, and cache status."""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.database import get_db
from app.redis_client import get_redis_client

router = APIRouter(prefix="/health", tags=["Health"])
test_router = APIRouter(prefix="/test", tags=["test"])

TEST_MARKDOWN = """# Markdown Rendering Test

## Overview
This is a **test response** to verify that markdown rendering is working correctly in the frontend.

## Features to Check
- **Bold text** should appear bold
- *Italic text* should appear italic
- `Inline code` should have a different background

### Code Block
```python
def test_function():
    return "Hello, World!"
```

### Blockquote
> This is a blockquote. It should have a left border.
"""


@router.get("/", summary="Basic health status")
async def health_check() -> Dict[str, Any]:
    """Basic health check indicating the ASGI service is responsive."""
    return {
        "status": "healthy",
        "service": "MOOD AI Agent",
        "version": "1.0.0"
    }


@router.get("/db", summary="PostgreSQL connection health check")
async def health_check_db(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Execute a simple query to verify PostgreSQL database connectivity."""
    try:
        await db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}"
        )


@router.get("/redis", summary="Redis cache health check")
async def health_check_redis(redis_client: redis.Redis = Depends(get_redis_client)) -> Dict[str, Any]:
    """Ping Redis to verify cache connectivity."""
    try:
        await redis_client.ping()
        return {
            "status": "healthy",
            "redis": "connected"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Redis connection failed: {str(e)}"
        )


@test_router.get("/markdown", summary="Markdown test snippet")
async def test_markdown_rendering() -> Dict[str, Any]:
    """Test endpoint returning sample Markdown for frontend render validation."""
    return {
        "response": TEST_MARKDOWN,
        "session_id": "test-session",
        "test": True
    }
