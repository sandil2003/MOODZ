"""Async Redis client management and caching utility functions."""

from typing import Optional
import redis.asyncio as redis
from config import settings

# Global Redis client instance
redis_client: Optional[redis.Redis] = None


async def get_redis_client() -> redis.Redis:
    """Retrieve or create the global async Redis client."""
    global redis_client
    if redis_client is None:
        redis_client = await redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=10,
        )
    return redis_client


async def close_redis() -> None:
    """Close the global Redis connection gracefully."""
    global redis_client
    if redis_client is not None:
        await redis_client.close()
        redis_client = None


async def cache_get(key: str) -> Optional[str]:
    """Get a string value from Redis by key."""
    client = await get_redis_client()
    return await client.get(key)


async def cache_set(key: str, value: str, expire: int = 3600) -> bool:
    """Set a string value with TTL in Redis."""
    client = await get_redis_client()
    return bool(await client.setex(key, expire, value))


async def cache_delete(key: str) -> bool:
    """Delete a key from Redis."""
    client = await get_redis_client()
    return bool(await client.delete(key) > 0)
