"""Redis-based session manager for short-term conversational memory and context buffering."""

import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union
from uuid import UUID
import redis.asyncio as redis

from config import settings

logger = logging.getLogger(__name__)


def _to_uuid_str(val: Union[str, UUID]) -> str:
    """Helper ensuring string representation of UUID."""
    return str(val)


class SessionManager:
    """Manages short-term conversation history stored in Redis lists."""

    def __init__(self, redis_client: redis.Redis, ttl_seconds: int = 3600):
        self.redis = redis_client
        self.ttl_seconds = ttl_seconds
        self.key_prefix = "session:"

    def _get_session_key(self, session_id: Union[str, UUID]) -> str:
        return f"{self.key_prefix}{_to_uuid_str(session_id)}"

    async def add_message_to_session(
        self,
        session_id: Union[str, UUID],
        message: Dict[str, Any],
        extend_ttl: bool = True
    ) -> bool:
        """Push a message onto the session's Redis list and refresh its expiration."""
        try:
            key = self._get_session_key(session_id)
            if "timestamp" not in message:
                message["timestamp"] = datetime.now(timezone.utc).isoformat()

            message_json = json.dumps(message)
            await self.redis.rpush(key, message_json)
            if extend_ttl:
                await self.redis.expire(key, self.ttl_seconds)
            return True
        except Exception as e:
            logger.error(f"Error adding message to session {session_id}: {e}")
            return False

    async def get_recent_history(
        self,
        session_id: Union[str, UUID],
        limit: int = 10,
        extend_ttl: bool = False
    ) -> List[Dict[str, Any]]:
        """Retrieve the N most recent message dictionaries from Redis."""
        try:
            key = self._get_session_key(session_id)
            messages_json = await self.redis.lrange(key, -limit, -1)
            messages: List[Dict[str, Any]] = []

            for msg_json in messages_json:
                try:
                    messages.append(json.loads(msg_json))
                except (json.JSONDecodeError, TypeError):
                    continue

            if extend_ttl and messages:
                await self.redis.expire(key, self.ttl_seconds)
            return messages
        except Exception as e:
            logger.error(f"Error getting history for session {session_id}: {e}")
            return []

    async def get_full_history(self, session_id: Union[str, UUID]) -> List[Dict[str, Any]]:
        """Retrieve all messages stored for a session."""
        try:
            key = self._get_session_key(session_id)
            messages_json = await self.redis.lrange(key, 0, -1)
            messages: List[Dict[str, Any]] = []

            for msg_json in messages_json:
                try:
                    messages.append(json.loads(msg_json))
                except (json.JSONDecodeError, TypeError):
                    continue
            return messages
        except Exception as e:
            logger.error(f"Error getting full history for session {session_id}: {e}")
            return []

    async def get_session_length(self, session_id: Union[str, UUID]) -> int:
        """Get the total count of messages currently stored in the session."""
        try:
            key = self._get_session_key(session_id)
            return await self.redis.llen(key)
        except Exception as e:
            logger.error(f"Error getting session length for {session_id}: {e}")
            return 0

    async def clear_session(self, session_id: Union[str, UUID]) -> bool:
        """Delete all messages for a session from Redis."""
        try:
            key = self._get_session_key(session_id)
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error clearing session {session_id}: {e}")
            return False

    async def session_exists(self, session_id: Union[str, UUID]) -> bool:
        """Check if an active session key exists in Redis."""
        try:
            key = self._get_session_key(session_id)
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Error checking session existence for {session_id}: {e}")
            return False

    async def get_session_ttl(self, session_id: Union[str, UUID]) -> int:
        """Get remaining TTL (seconds) for a session key."""
        try:
            key = self._get_session_key(session_id)
            return await self.redis.ttl(key)
        except Exception as e:
            logger.error(f"Error getting TTL for session {session_id}: {e}")
            return -2

    async def extend_session_ttl(
        self,
        session_id: Union[str, UUID],
        additional_seconds: Optional[int] = None
    ) -> bool:
        """Extend session TTL."""
        try:
            key = self._get_session_key(session_id)
            ttl = additional_seconds or self.ttl_seconds
            await self.redis.expire(key, ttl)
            return True
        except Exception as e:
            logger.error(f"Error extending TTL for session {session_id}: {e}")
            return False

    async def get_active_sessions(self) -> List[str]:
        """Scan and list all active session IDs in Redis."""
        try:
            pattern = f"{self.key_prefix}*"
            keys: List[str] = []
            async for key in self.redis.scan_iter(match=pattern):
                key_str = key.decode("utf-8") if isinstance(key, bytes) else str(key)
                keys.append(key_str.replace(self.key_prefix, ""))
            return keys
        except Exception as e:
            logger.error(f"Error getting active sessions: {e}")
            return []

    async def add_user_message(
        self,
        session_id: Union[str, UUID],
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Convenience method to push a user message turn."""
        message = {
            "role": "user",
            "content": content,
            "metadata": metadata or {}
        }
        return await self.add_message_to_session(session_id, message)

    async def add_assistant_message(
        self,
        session_id: Union[str, UUID],
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Convenience method to push an assistant response turn."""
        message = {
            "role": "assistant",
            "content": content,
            "metadata": metadata or {}
        }
        return await self.add_message_to_session(session_id, message)


_session_manager: Optional[SessionManager] = None


async def get_session_manager() -> SessionManager:
    """Singleton getter for the global SessionManager."""
    global _session_manager
    if _session_manager is None:
        from app.redis_client import get_redis_client
        client = await get_redis_client()
        _session_manager = SessionManager(client, ttl_seconds=settings.session_ttl_seconds)
    return _session_manager
