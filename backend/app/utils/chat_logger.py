"""Chat conversation logger storing scrubbed dialogues to JSON Lines (JSONL) on disk."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
from uuid import UUID
import aiofiles

from app.core.pii_scrubber import PIIScrubber

logger = logging.getLogger(__name__)


class ChatLogger:
    """Async logger writing scrubbed conversation turns and metadata to disk."""

    def __init__(self, log_dir: str = "logs", log_file: str = "chats.jsonl"):
        self.log_dir = Path(log_dir)
        self.log_file = self.log_dir / log_file
        self.log_dir.mkdir(parents=True, exist_ok=True)

    async def log_chat(
        self,
        user_id: UUID,
        session_id: UUID,
        prompt: str,
        response: str,
        latency: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Sanitize PII and append conversation turn to chats.jsonl."""
        try:
            clean_prompt = PIIScrubber.scrub_text(prompt)
            clean_response = PIIScrubber.scrub_text(response)
            clean_meta = PIIScrubber.scrub_dict(metadata) if metadata else None

            log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": str(user_id),
                "session_id": str(session_id),
                "prompt": clean_prompt,
                "response": clean_response,
                "latency": round(latency, 3),
            }
            if clean_meta:
                log_entry["metadata"] = clean_meta

            async with aiofiles.open(self.log_file, mode="a", encoding="utf-8") as f:
                await f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Error logging chat to disk: {e}")

    async def read_logs(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Read chat logs from file in reverse-chronological order."""
        if not self.log_file.exists():
            return []

        try:
            logs: List[Dict[str, Any]] = []
            async with aiofiles.open(self.log_file, mode="r", encoding="utf-8") as f:
                async for line in f:
                    if line.strip():
                        logs.append(json.loads(line))

            logs.reverse()
            return logs[:limit] if limit else logs
        except Exception as e:
            logger.error(f"Error reading chat logs: {e}")
            return []

    async def get_user_logs(self, user_id: UUID, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Filter logs for a specific user ID."""
        all_logs = await self.read_logs()
        user_logs = [log for log in all_logs if log.get("user_id") == str(user_id)]
        return user_logs[:limit] if limit else user_logs

    async def get_session_logs(self, session_id: UUID) -> List[Dict[str, Any]]:
        """Filter logs for a specific chat session."""
        all_logs = await self.read_logs()
        return [log for log in all_logs if log.get("session_id") == str(session_id)]

    def get_log_stats(self) -> Dict[str, Any]:
        """Return file size and total log count."""
        if not self.log_file.exists():
            return {"total_logs": 0, "file_size": 0, "file_path": str(self.log_file)}

        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                total_logs = sum(1 for line in f if line.strip())

            file_size = self.log_file.stat().st_size
            return {
                "total_logs": total_logs,
                "file_size": file_size,
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "file_path": str(self.log_file)
            }
        except Exception as e:
            logger.error(f"Error getting log stats: {e}")
            return {}


_chat_logger: Optional[ChatLogger] = None


def get_chat_logger() -> ChatLogger:
    """Retrieve global ChatLogger singleton instance."""
    global _chat_logger
    if _chat_logger is None:
        _chat_logger = ChatLogger()
    return _chat_logger
