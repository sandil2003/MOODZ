"""Security audit logging module for authentication events and threat detection."""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

logger = logging.getLogger("moodz.security")
logger.setLevel(logging.INFO)

# Ensure console handler is configured
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[SECURITY_AUDIT] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def _mask_ip(ip: Optional[str]) -> str:
    """Mask client IP address to comply with privacy best practices."""
    if not ip or ip == "unknown":
        return "unknown"
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.***.***"
    # IPv6 or other
    return ip[:min(len(ip), 8)] + ":****"


def log_security_event(
    event_type: str,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    success: bool = True,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Record an immutable, structured security audit event.
    
    Event types:
    - auth.login.success
    - auth.login.failed
    - auth.account.locked
    - auth.mfa.required
    - auth.mfa.success
    - auth.mfa.failed
    - auth.token.refreshed
    - auth.token.reuse_detected
    - auth.session.revoked
    - auth.password.changed
    - auth.register.success
    """
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        "success": success,
        "user_id": user_id or "anonymous",
        "client_ip_masked": _mask_ip(ip_address),
        "user_agent": user_agent[:100] if user_agent else "unknown",
        "details": details or {},
    }

    log_level = logging.INFO if success else logging.WARNING
    if "locked" in event_type or "reuse_detected" in event_type:
        log_level = logging.ERROR

    logger.log(log_level, json.dumps(record))
