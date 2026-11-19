"""Backward-compatibility shim for Redis client access."""

from app.core.redis_client import (
    redis_client,
    get_redis_client,
    close_redis,
    cache_get,
    cache_set,
    cache_delete
)

__all__ = [
    "redis_client",
    "get_redis_client",
    "close_redis",
    "cache_get",
    "cache_set",
    "cache_delete"
]
