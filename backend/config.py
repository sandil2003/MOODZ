"""Backward-compatibility shim for settings/config."""
from app.core.config import settings, Settings

__all__ = ["settings", "Settings"]
