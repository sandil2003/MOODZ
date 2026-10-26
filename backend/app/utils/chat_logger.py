import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from uuid import UUID
import aiofiles


class ChatLogger:
    """
    Logger for chat conversations to JSONL file.
    
    Logs each conversation with:
    - timestamp: ISO format timestamp
    - user_id: User UUID
    - session_id: Session UUID
    - prompt: User message
    - response: AI response
    - latency: Response time in seconds
    - metadata: Additional context (optional)
    """
    
    def __init__(self, log_dir: str = "logs", log_file: str = "chats.jsonl"):
        """
        Initialize chat logger.
        
        Args:
            log_dir: Directory to store logs
            log_file: Name of the JSONL log file
        """
        self.log_dir = Path(log_dir)
        self.log_file = self.log_dir / log_file
        
        # Create log directory if it doesn't exist
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    async def log_chat(
        self,
        user_id: UUID,
        session_id: UUID,
        prompt: str,
        response: str,
        latency: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log a chat conversation to JSONL file.
        
        Args:
            user_id: User UUID
            session_id: Session UUID
            prompt: User message
            response: AI response
            latency: Response time in seconds
            metadata: Additional context (optional)
        """
        try:
            # Prepare log entry
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": str(user_id),
                "session_id": str(session_id),
                "prompt": prompt,
                "response": response,
                "latency": round(latency, 3),
            }
            
            # Add metadata if provided
            if metadata:
                log_entry["metadata"] = metadata
            
            # Append to JSONL file
            async with aiofiles.open(self.log_file, mode='a', encoding='utf-8') as f:
                await f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
                
        except Exception as e:
            # Log errors but don't fail the request
            print(f"Error logging chat: {e}")
    
    async def read_logs(self, limit: Optional[int] = None) -> list[Dict[str, Any]]:
        """
        Read chat logs from JSONL file.
        
        Args:
            limit: Maximum number of logs to return (most recent first)
            
        Returns:
            List of log entries
        """
        try:
            if not self.log_file.exists():
                return []
            
            logs = []
            async with aiofiles.open(self.log_file, mode='r', encoding='utf-8') as f:
                async for line in f:
                    if line.strip():
                        logs.append(json.loads(line))
            
            # Return most recent first
            logs.reverse()
            
            if limit:
                return logs[:limit]
            
            return logs
            
        except Exception as e:
            print(f"Error reading logs: {e}")
            return []
    
    async def get_user_logs(
        self,
        user_id: UUID,
        limit: Optional[int] = None
    ) -> list[Dict[str, Any]]:
        """
        Get chat logs for a specific user.
        
        Args:
            user_id: User UUID
            limit: Maximum number of logs to return
            
        Returns:
            List of log entries for the user
        """
        all_logs = await self.read_logs()
        user_logs = [
            log for log in all_logs
            if log.get("user_id") == str(user_id)
        ]
        
        if limit:
            return user_logs[:limit]
        
        return user_logs
    
    async def get_session_logs(
        self,
        session_id: UUID
    ) -> list[Dict[str, Any]]:
        """
        Get chat logs for a specific session.
        
        Args:
            session_id: Session UUID
            
        Returns:
            List of log entries for the session
        """
        all_logs = await self.read_logs()
        return [
            log for log in all_logs
            if log.get("session_id") == str(session_id)
        ]
    
    def get_log_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the log file.
        
        Returns:
            Dictionary with log statistics
        """
        try:
            if not self.log_file.exists():
                return {
                    "total_logs": 0,
                    "file_size": 0,
                    "file_path": str(self.log_file)
                }
            
            # Count lines
            with open(self.log_file, 'r', encoding='utf-8') as f:
                total_logs = sum(1 for line in f if line.strip())
            
            # Get file size
            file_size = self.log_file.stat().st_size
            
            return {
                "total_logs": total_logs,
                "file_size": file_size,
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "file_path": str(self.log_file)
            }
            
        except Exception as e:
            print(f"Error getting log stats: {e}")
            return {}


# Global logger instance
_chat_logger: Optional[ChatLogger] = None


def get_chat_logger() -> ChatLogger:
    """
    Get or create the global chat logger instance.
    
    Returns:
        ChatLogger: Logger instance
    """
    global _chat_logger
    
    if _chat_logger is None:
        _chat_logger = ChatLogger()
    
    return _chat_logger
