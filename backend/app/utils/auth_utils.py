"""Backward-compatibility shim for auth utilities."""

from app.core.auth_utils import (
    hash_password,
    verify_password,
    verify_and_migrate_password,
    create_access_token,
    create_refresh_token,
    create_mfa_ticket,
    decode_access_token,
    set_auth_cookies,
    clear_auth_cookies,
    get_current_user_id,
    oauth2_scheme,
)

__all__ = [
    "hash_password",
    "verify_password",
    "verify_and_migrate_password",
    "create_access_token",
    "create_refresh_token",
    "create_mfa_ticket",
    "decode_access_token",
    "set_auth_cookies",
    "clear_auth_cookies",
    "get_current_user_id",
    "oauth2_scheme",
]
