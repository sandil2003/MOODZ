import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID
import redis.asyncio as redis
from config import settings


class SessionManager:
    """
    Redis-based session manager for short-term memory.
    
    Handles conversation history with automatic TTL (Time To Live) expiry.
    Each session stores messages in a Redis list with automatic cleanup.
    """
    
    def __init__(self, redis_client: redis.Redis, ttl_seconds: int = 3600):
        """
        Initialize session manager.
        
        Args:
            redis_client: Async Redis client instance
            ttl_seconds: Time to live for sessions in seconds (default: 1 hour)
        """
        self.redis = redis_client
        self.ttl_seconds = ttl_seconds
        self.key_prefix = "session:"
    
    def _get_session_key(self, session_id: UUID) -> str:
        """
        Generate Redis key for session.
        
        Args:
            session_id: Session UUID
            
        Returns:
            str: Redis key
        """
        return f"{self.key_prefix}{str(session_id)}"
    
    async def add_message_to_session(
        self,
        session_id: UUID,
        message: Dict[str, Any],
        extend_ttl: bool = True
    ) -> bool:
        """
        Add a message to a session's conversation history.
        
        Args:
            session_id: Session UUID
            message: Message dictionary containing role, content, timestamp, etc.
            extend_ttl: Whether to extend session TTL on new message (default: True)
            
        Returns:
            bool: True if successful
            
        Example message format:
            {
                "role": "user",  # or "assistant"
                "content": "Hello, how are you?",
                "timestamp": "2025-12-07T14:30:00",
                "metadata": {"mood_score": 7}
            }
        """
        try:
            key = self._get_session_key(session_id)
            
            # Add timestamp if not present
            if "timestamp" not in message:
                message["timestamp"] = datetime.utcnow().isoformat()
            
            # Serialize message to JSON
            message_json = json.dumps(message)
            
            # Add message to Redis list (RPUSH adds to end)
            await self.redis.rpush(key, message_json)
            
            # Set or extend TTL
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
        """
        Get recent conversation history from a session.
        
        Args:
            session_id: Session UUID
            limit: Maximum number of messages to retrieve (default: 10)
            extend_ttl: Whether to extend session TTL on access (default: False)
            
        Returns:
            List[Dict]: List of message dictionaries, most recent last
        """
        try:
            key = self._get_session_key(session_id)
            
            # Get last N messages from Redis list
            # LRANGE with negative indices: -limit to -1 gets last N items
            messages_json = await self.redis.lrange(key, -limit, -1)
            
            # Deserialize messages
            messages = []
            for msg_json in messages_json:
                try:
                    message = json.loads(msg_json)
                    messages.append(message)
                except json.JSONDecodeError:
                    print(f"Failed to decode message: {msg_json}")
                    continue
            
            # Optionally extend TTL on access
            if extend_ttl and messages:
                await self.redis.expire(key, self.ttl_seconds)
            
            return messages
            
        except Exception as e:
            print(f"Error getting history for session {session_id}: {e}")
            return []
    
    async def get_full_history(self, session_id: UUID) -> List[Dict[str, Any]]:
        """
        Get entire conversation history for a session.
        
        Args:
            session_id: Session UUID
            
        Returns:
            List[Dict]: All messages in the session
        """
        try:
            key = self._get_session_key(session_id)
            
            # Get all messages (0 to -1 means all)
            messages_json = await self.redis.lrange(key, 0, -1)
            
            messages = []
            for msg_json in messages_json:
                try:
                    message = json.loads(msg_json)
                    messages.append(message)
                except json.JSONDecodeError:
                    continue
            
            return messages
            
        except Exception as e:
            print(f"Error getting full history for session {session_id}: {e}")
            return []
    
    async def get_session_length(self, session_id: UUID) -> int:
        """
        Get the number of messages in a session.
        
        Args:
            session_id: Session UUID
            
        Returns:
            int: Number of messages
        """
        try:
            key = self._get_session_key(session_id)
            return await self.redis.llen(key)
        except Exception as e:
            print(f"Error getting session length for {session_id}: {e}")
            return 0
    
    async def clear_session(self, session_id: UUID) -> bool:
        """
        Clear all messages from a session.
        
        Args:
            session_id: Session UUID
            
        Returns:
            bool: True if successful
        """
        try:
            key = self._get_session_key(session_id)
            await self.redis.delete(key)
            return True
        except Exception as e:
            print(f"Error clearing session {session_id}: {e}")
            return False
    
    async def session_exists(self, session_id: UUID) -> bool:
        """
        Check if a session exists.
        
        Args:
            session_id: Session UUID
            
        Returns:
            bool: True if session exists
        """
        try:
            key = self._get_session_key(session_id)
            return await self.redis.exists(key) > 0
        except Exception as e:
            print(f"Error checking session existence for {session_id}: {e}")
            return False
    
    async def get_session_ttl(self, session_id: UUID) -> int:
        """
        Get remaining TTL for a session.
        
        Args:
            session_id: Session UUID
            
        Returns:
            int: Remaining seconds, -1 if no expiry, -2 if doesn't exist
        """
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
        """
        Extend the TTL of a session.
        
        Args:
            session_id: Session UUID
            additional_seconds: Seconds to extend (default: use default TTL)
            
        Returns:
            bool: True if successful
        """
        try:
            key = self._get_session_key(session_id)
            ttl = additional_seconds if additional_seconds else self.ttl_seconds
            await self.redis.expire(key, ttl)
            return True
        except Exception as e:
            print(f"Error extending TTL for session {session_id}: {e}")
            return False
    
    async def get_active_sessions(self) -> List[str]:
        """
        Get list of all active session IDs.
        
        Returns:
            List[str]: List of session ID strings
        """
        try:
            pattern = f"{self.key_prefix}*"
            keys = []
            
            # Scan for all session keys
            async for key in self.redis.scan_iter(match=pattern):
                # Handle both bytes and string keys
                if isinstance(key, bytes):
                    key = key.decode('utf-8')
                # Extract session ID from key
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
        """
        Convenience method to add a user message.
        
        Args:
            session_id: Session UUID
            content: Message content
            metadata: Optional metadata dictionary
            
        Returns:
            bool: True if successful
        """
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
        """
        Convenience method to add an assistant message.
        
        Args:
            session_id: Session UUID
            content: Message content
            metadata: Optional metadata dictionary
            
        Returns:
            bool: True if successful
        """
        message = {
            "role": "assistant",
            "content": content,
            "metadata": metadata or {}
        }
        return await self.add_message_to_session(session_id, message)


# Global session manager instance
_session_manager: Optional[SessionManager] = None


async def get_session_manager() -> SessionManager:
    """
    Get or create the global session manager instance.
    
    Returns:
        SessionManager: Session manager instance
    """
    global _session_manager
    
    if _session_manager is None:
        from app.redis_client import get_redis_client
        redis_client = await get_redis_client()
        
        # Default TTL: 1 hour (3600 seconds)
        # Can be configured via environment variable
        ttl = 3600
        
        _session_manager = SessionManager(redis_client, ttl_seconds=ttl)
    
    return _session_manager
