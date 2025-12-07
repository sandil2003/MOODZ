from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.redis_client import get_redis_client
import redis.asyncio as redis

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/")
async def health_check():
    """
    Basic health check endpoint.
    
    Returns:
        dict: Health status
    """
    return {
        "status": "healthy",
        "service": "MOOD AI Agent",
        "version": "1.0.0"
    }


@router.get("/db")
async def health_check_db(db: AsyncSession = Depends(get_db)):
    """
    Database health check endpoint.
    
    Args:
        db: Database session
        
    Returns:
        dict: Database health status
        
    Raises:
        HTTPException: If database is not accessible
    """
    try:
        # Execute a simple query to check database connectivity
        await db.execute("SELECT 1")
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
    """
    Redis health check endpoint.
    
    Args:
        redis_client: Redis client instance
        
    Returns:
        dict: Redis health status
        
    Raises:
        HTTPException: If Redis is not accessible
    """
    try:
        # Ping Redis to check connectivity
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
