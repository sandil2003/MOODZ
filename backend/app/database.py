"""Backward-compatibility shim for database access."""

from app.core.database import (
    Base,
    AsyncSessionLocal,
    engine,
    get_db,
    init_db,
    close_db
)

__all__ = [
    "Base",
    "AsyncSessionLocal",
    "engine",
    "get_db",
    "init_db",
    "close_db"
]
