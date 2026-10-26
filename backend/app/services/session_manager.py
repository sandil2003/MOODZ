from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from uuid import UUID
import json
import redis.asyncio as redis
from config import settings

class SessionManager:
    """
    Redis-based session manager for short-term memory.
    """
    def __init__(self, redis_client: redis.Redis, ttl_seconds: int = 3600):
        self.redis = redis_client
        self.ttl_seconds = ttl_seconds
        self.key_prefix = "session:"
        
    def _get_session_key(self, session_id: UUID) -> str:
        return f"{self.key_prefix}{str(session_id)}"
        
    async def add_message_to_session(
        self,
        session_id: UUID,
        message: Dict[str, Any],
        extend_ttl: bool = True
    ) -> bool:
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
            print(f"Error adding message to session {session_id}: {e}")
            return False
            
    async def get_recent_history(
        self,
        session_id: UUID,
        limit: int = 10,
        extend_ttl: bool = False
    ) -> List[Dict[str, Any]]:
        try:
            key = self._get_session_key(session_id)
            messages_json = await self.redis.lrange(key, -limit, -1)
            messages = []
            for msg_json in messages_json:
                try:
                    message = json.loads(msg_json)
                    messages.append(message)
                except json.JSONDecodeError:
                    continue
            if extend_ttl and messages:
                await self.redis.expire(key, self.ttl_seconds)
            return messages
        except Exception as e:
            print(f"Error getting history for session {session_id}: {e}")
            return []
            
    async def get_full_history(self, session_id: UUID) -> List[Dict[str, Any]]:
        try:
            key = self._get_session_key(session_id)
            messages_json = await self.redis.lrange(key, 0, -1)
            messages = []
            for msg_json in messages_json:
                try:
                    message = json.loads(msg_json)
                    messages.append(message)
                except:
                    continue
            return messages
        except Exception as e:
            print(f"Error getting full history for session {session_id}: {e}")
            return []
            
    async def get_session_length(self, session_id: UUID) -> int:
        try:
            key = self._get_session_key(session_id)
            return await self.redis.llen(key)
        except Exception as e:
            print(f"Error getting session length for {session_id}: {e}")
            return 0
            
    async def clear_session(self, session_id: UUID) -> bool:
        try:
            key = self._get_session_key(session_id)
            await self.redis.delete(key)
            return True
        except Exception as e:
            print(f"Error clearing session {session_id}: {e}")
            return False
            
    async def session_exists(self, session_id: UUID) -> bool:
        try:
            key = self._get_session_key(session_id)
            return await self.redis.exists(key) > 0
        except Exception as e:
            print(f"Error checking session existence for {session_id}: {e}")
            return False
            
    async def get_session_ttl(self, session_id: UUID) -> int:
        try:
            key = self._get_session_key(session_id)
            return await self.redis.ttl(key)
        except Exception as e:
            print(f"Error getting TTL for session {session_id}: {e}")
            return -2
            
    async def extend_session_ttl(
        self,
        session_id: UUID,
        additional_seconds: Optional[int] = None
    ) -> bool:
        try:
            key = self._get_session_key(session_id)
            ttl = additional_seconds if additional_seconds else self.ttl_seconds
            await self.redis.expire(key, ttl)
            return True
        except Exception as e:
            print(f"Error extending TTL for session {session_id}: {e}")
            return False
            
    async def get_active_sessions(self) -> List[str]:
        try:
            pattern = f"{self.key_prefix}*"
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                if isinstance(key, bytes):
                    key = key.decode('utf-8')
                session_id = key.replace(self.key_prefix, '')
                keys.append(session_id)
            return keys
        except Exception as e:
            print(f"Error getting active sessions: {e}")
            return []
            
    async def add_user_message(
        self,
        session_id: UUID,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        message = {
            "role": "user",
            "content": content,
            "metadata": metadata or {}
        }
        return await self.add_message_to_session(session_id, message)
        
    async def add_assistant_message(
        self,
        session_id: UUID,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        message = {
            "role": "assistant",
            "content": content,
            "metadata": metadata or {}
        }
        return await self.add_message_to_session(session_id, message)


_session_manager: Optional[SessionManager] = None


async def get_session_manager() -> SessionManager:
    global _session_manager
    if _session_manager is None:
        from app.redis_client import get_redis_client
        redis_client = await get_redis_client()
        _session_manager = SessionManager(redis_client, ttl_seconds=settings.session_ttl_seconds)
    return _session_manager
