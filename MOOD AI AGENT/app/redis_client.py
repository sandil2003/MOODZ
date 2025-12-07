import redis.asyncio as redis
from typing import Optional
from config import settings

# Global Redis client instance
redis_client: Optional[redis.Redis] = None


async def get_redis_client() -> redis.Redis:
    """
    Get Redis client instance.
    
    Returns:
        redis.Redis: Redis client
    """
    global redis_client
    if redis_client is None:
        redis_client = await redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=10,
        )
    return redis_client


async def close_redis():
    """Close Redis connection."""
    global redis_client
    if redis_client:
        await redis_client.close()


async def cache_get(key: str) -> Optional[str]:
    """
    Get value from cache.
    
    Args:
        key: Cache key
        
    Returns:
        Optional[str]: Cached value or None
    """
    client = await get_redis_client()
    return await client.get(key)


async def cache_set(key: str, value: str, expire: int = 3600) -> bool:
    """
    Set value in cache.
    
    Args:
        key: Cache key
        value: Value to cache
        expire: Expiration time in seconds (default: 1 hour)
        
    Returns:
        bool: True if successful
    """
    client = await get_redis_client()
    return await client.setex(key, expire, value)


async def cache_delete(key: str) -> bool:
    """
    Delete value from cache.
    
    Args:
        key: Cache key
        
    Returns:
        bool: True if successful
    """
    client = await get_redis_client()
    return await client.delete(key) > 0
