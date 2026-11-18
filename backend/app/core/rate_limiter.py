"""Rate limiting infrastructure using SlowAPI with graceful fallback."""

import logging
from slowapi import Limiter
from slowapi.util import get_remote_address
from config import settings

logger = logging.getLogger("moodz.rate_limiter")

# Initialize limiter. In development/testing, default to in-memory store for isolation.
try:
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["120/minute"],
    )
except Exception as e:
    logger.warning(f"Failed to initialize Redis limiter, falling back to in-memory: {e}")
    limiter = Limiter(key_func=get_remote_address)
