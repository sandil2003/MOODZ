"""Authentication utility functions for Argon2id/bcrypt password hashing,
dual-token management (Access + Refresh), HttpOnly cookies, and FastAPI security dependencies.
"""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple

from jose import JWTError, jwt
from fastapi import Request, Response, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from config import settings
from app.core.security_crypto import (
    hash_password as crypto_hash_password,
    verify_and_update_password as crypto_verify_and_update,
)

# OAuth2 bearer token extractor
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    """Hash a plain-text password using Argon2id (with bcrypt backward compatibility)."""
    return crypto_hash_password(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a hashed password (Argon2id or bcrypt)."""
    is_valid, _ = crypto_verify_and_update(plain_password, hashed_password)
    return is_valid


def verify_and_migrate_password(plain_password: str, hashed_password: str) -> Tuple[bool, Optional[str]]:
    """Verify password and return a new Argon2id hash if the original was legacy bcrypt."""
    return crypto_verify_and_update(plain_password, hashed_password)


def hash_token(token: str) -> str:
    """Compute SHA-256 digest of a token for secure database/Redis storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Generate a signed short-lived JWT access token."""
    to_encode = data.copy()
    expire_duration = expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    expire_time = datetime.now(timezone.utc) + expire_duration

    to_encode.update({
        "exp": expire_time,
        "type": "access",
        "jti": str(uuid.uuid4()),
    })
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(user_id: str, session_id: str, family_id: str) -> str:
    """Generate a signed long-lived JWT refresh token bound to a session and family."""
    expire_time = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": str(user_id),
        "session_id": str(session_id),
        "family_id": str(family_id),
        "exp": expire_time,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_mfa_ticket(user_id: str) -> str:
    """Generate a temporary signed ticket for intermediate MFA verification (5-minute TTL)."""
    expire_time = datetime.now(timezone.utc) + timedelta(minutes=5)
    payload = {
        "sub": str(user_id),
        "type": "mfa_pending",
        "exp": expire_time,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str, expected_type: str = "access") -> Dict[str, Any]:
    """Decode and validate a JWT access or refresh token, verifying expiration and type."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        sub = payload.get("sub")
        if sub is None:
            raise credentials_exception

        token_type = payload.get("type", "access")
        if expected_type and token_type != expected_type:
            raise credentials_exception

        return payload
    except JWTError:
        raise credentials_exception


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: Optional[str] = None
) -> None:
    """Set hardened HttpOnly, Secure, SameSite cookies for authentication tokens."""
    # Access token cookie (valid across entire API)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
        domain=settings.cookie_domain,
    )

    if refresh_token:
        # Refresh token cookie (scoped to /api/auth to prevent transmission on general endpoints)
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
            max_age=settings.refresh_token_expire_days * 86400,
            path="/api/auth",
            domain=settings.cookie_domain,
        )


def clear_auth_cookies(response: Response) -> None:
    """Delete authentication cookies on logout or session invalidation."""
    response.delete_cookie(
        key="access_token",
        path="/",
        domain=settings.cookie_domain,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )
    response.delete_cookie(
        key="refresh_token",
        path="/api/auth",
        domain=settings.cookie_domain,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )


async def get_current_user_id(
    request: Request = None,
    token: Optional[str] = Depends(oauth2_scheme),
    bearer_token: Optional[str] = None
) -> str:
    """FastAPI dependency extracting the authenticated user ID ('sub').
    
    Checks in priority order:
    1. Explicit token argument (for test calls and direct invocations)
    2. HttpOnly 'access_token' cookie from request (browser standard)
    3. 'Authorization: Bearer <token>' header from request
    """
    candidate_token = token or bearer_token

    if candidate_token is None and request is not None:
        if "access_token" in request.cookies:
            candidate_token = request.cookies.get("access_token")
        else:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                candidate_token = auth_header.split(" ", 1)[1]

    if not candidate_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(candidate_token, expected_type="access")
    return payload["sub"]
