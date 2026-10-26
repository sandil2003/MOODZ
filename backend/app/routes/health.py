from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.redis_client import get_redis_client
import redis.asyncio as redis

router = APIRouter(prefix="/health", tags=["Health"])
test_router = APIRouter(prefix="/test", tags=["test"])

TEST_MARKDOWN = """# Markdown Rendering Test

## Overview
This is a **test response** to verify that markdown rendering is working correctly in the frontend.

## Features to Check

### Text Formatting
- **Bold text** should appear bold
- *Italic text* should appear italic
- `Inline code` should have a different background

### Lists
1. First ordered item
2. Second ordered item
3. Third ordered item

Unordered list:
- Apple
- Banana
- Cherry

### Code Block
```python
def test_function():
    return "Hello, World!"
```

### Blockquote
> This is a blockquote.
> It should have a left border.

## Summary
If all the above elements render correctly, then **markdown is working**! ✅

---
*Test completed successfully*
"""


@router.get("/")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "MOOD AI Agent",
        "version": "1.0.0"
    }


@router.get("/db")
async def health_check_db(db: AsyncSession = Depends(get_db)):
    """Database health check endpoint."""
    try:
        await db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database connection failed: {str(e)}"
        )


@router.get("/redis")
async def health_check_redis(redis_client: redis.Redis = Depends(get_redis_client)):
    """Redis health check endpoint."""
    try:
        await redis_client.ping()
        return {
            "status": "healthy",
            "redis": "connected"
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Redis connection failed: {str(e)}"
        )


@test_router.get("/markdown")
async def test_markdown_rendering():
    """Test endpoint that returns markdown-formatted text."""
    return {
        "response": TEST_MARKDOWN,
        "session_id": "test-session",
        "test": True
    }
