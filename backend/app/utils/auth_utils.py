"""Backward-compatibility shim for auth utilities."""

from app.core.auth_utils import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    get_current_user_id,
    oauth2_scheme
)

__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "get_current_user_id",
    "oauth2_scheme"
]
