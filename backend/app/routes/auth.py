"""Authentication and authorization endpoints for the MOODZ mental wellness platform.

Implements NIST SP 800-63B and OWASP ASVS compliant authentication:
- Argon2id password hashing with automatic transparent migration of legacy bcrypt hashes
- Breached & weak password validation via HIBP k-Anonymity
- Anti-brute-force rate limiting and progressive account lockout
- Timing-attack neutralization (constant-time verification)
- Dual-token architecture (15m Access Token + 7d Refresh Token) stored in HttpOnly cookies
- Refresh Token Rotation (RTR) with family reuse detection (automatic breach revocation)
- Time-based One-Time Passwords (TOTP RFC 6238) MFA + single-use backup recovery codes
- Multi-device active session tracking and remote revocation
- Structured JSON security audit logging
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, UserSession
from app.schemas import (
    UserCreate,
    UserLogin,
    UserResponse,
    AuthResponse,
    MfaVerifyRequest,
    MfaSetupResponse,
    MfaActivateRequest,
    MfaActivateResponse,
    SessionResponse,
)
from app.core.auth_utils import (
    hash_password,
    verify_and_migrate_password,
    hash_token,
    create_access_token,
    create_refresh_token,
    create_mfa_ticket,
    decode_access_token,
    set_auth_cookies,
    clear_auth_cookies,
    get_current_user_id,
)
from app.core.security_crypto import validate_password_strength, verify_dummy_password
from app.core.mfa_service import (
    generate_totp_secret,
    generate_provisioning_uri,
    generate_qr_code_base64,
    verify_totp_code,
    generate_backup_codes,
    verify_and_consume_backup_code,
)
from app.core.security_audit import log_security_event
from app.core.rate_limiter import limiter
from config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger("moodz.auth")


def _get_client_ip(request: Request) -> str:
    """Extract client IP from headers or connection."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _get_user_agent(request: Request) -> str:
    """Extract client User-Agent string."""
    return request.headers.get("User-Agent", "unknown")


# ==============================================================================
# 1. User Registration
# ==============================================================================

@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
@limiter.limit("10/minute")
async def register(
    request: Request,
    response: Response,
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> AuthResponse:
    """Register a new user account with NIST SP 800-63B password validation and Argon2id hashing."""
    client_ip = _get_client_ip(request)
    user_agent = _get_user_agent(request)

    # 1. Enforce password presence
    if not user_data.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is required for registration",
        )

    # 2. NIST SP 800-63B strength and breach validation
    is_valid, error_msg = await validate_password_strength(
        user_data.password,
        user_inputs=[user_data.name, user_data.email] if user_data.email else [user_data.name]
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg or "Password does not meet security requirements.",
        )

    # 3. Check email uniqueness
    if user_data.email:
        result = await db.execute(select(User).where(User.email == user_data.email))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists",
            )

    # 4. Create and persist user with Argon2id hash
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        preferences=user_data.preferences or {},
        role=user_data.role or "user",
        is_active=True,
        mfa_enabled=False,
        failed_login_attempts=0,
    )
    db.add(new_user)

    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected database error during user registration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating your account. Please try again.",
        )
    await db.refresh(new_user)

    # 5. Create user session & tokens
    session_id = uuid.uuid4()
    family_id = uuid.uuid4()
    access_token = create_access_token(data={"sub": str(new_user.id), "session_id": str(session_id)})
    refresh_token = create_refresh_token(
        user_id=str(new_user.id),
        session_id=str(session_id),
        family_id=str(family_id)
    )

    # Persist session record
    session_rec = UserSession(
        id=session_id,
        user_id=new_user.id,
        refresh_token_hash=hash_token(refresh_token),
        family_id=family_id,
        ip_address=client_ip,
        user_agent=user_agent,
        expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(session_rec)
    await db.commit()

    # 6. Set HttpOnly cookies
    set_auth_cookies(response, access_token=access_token, refresh_token=refresh_token)

    log_security_event(
        "auth.register.success",
        user_id=str(new_user.id),
        ip_address=client_ip,
        user_agent=user_agent,
        success=True
    )

    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(new_user),
    )


# ==============================================================================
# 2. Login Endpoint with Brute-Force & Lockout Defenses
# ==============================================================================

@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Login with email and password",
)
@limiter.limit("10/minute")
async def login(
    request: Request,
    response: Response,
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
) -> AuthResponse:
    """Authenticate user with brute-force lockout, timing defense, and MFA challenge."""
    client_ip = _get_client_ip(request)
    user_agent = _get_user_agent(request)
    now_utc = datetime.now(timezone.utc)

    # 1. Fetch user by email
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()

    # 2. Defense against account enumeration: constant-time dummy verification
    if not user:
        verify_dummy_password()
        log_security_event(
            "auth.login.failed",
            user_id=None,
            ip_address=client_ip,
            user_agent=user_agent,
            success=False,
            details={"reason": "user_not_found"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # 3. Check account lockout state
    if user.locked_until:
        # Normalize locked_until for timezone comparison
        locked_until_tz = user.locked_until
        if locked_until_tz.tzinfo is None:
            locked_until_tz = locked_until_tz.replace(tzinfo=timezone.utc)

        if locked_until_tz > now_utc:
            remaining_seconds = int((locked_until_tz - now_utc).total_seconds())
            remaining_minutes = max(1, remaining_seconds // 60)
            log_security_event(
                "auth.account.locked",
                user_id=str(user.id),
                ip_address=client_ip,
                user_agent=user_agent,
                success=False,
                details={"remaining_seconds": remaining_seconds}
            )
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Account is temporarily locked due to excessive failed attempts. Please try again in {remaining_minutes} minute(s).",
            )
        else:
            # Lockout expired, clear lockout
            user.locked_until = None
            user.failed_login_attempts = 0

    # 4. Verify password with transparent Argon2id migration
    is_valid, new_argon2_hash = verify_and_migrate_password(
        credentials.password,
        user.hashed_password or ""
    )

    if not is_valid:
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        details = {"failed_attempts": user.failed_login_attempts}

        if user.failed_login_attempts >= settings.max_failed_login_attempts:
            user.locked_until = now_utc.replace(tzinfo=None) + timedelta(minutes=settings.lockout_duration_minutes)
            details["lockout_applied"] = True
            log_security_event(
                "auth.account.locked",
                user_id=str(user.id),
                ip_address=client_ip,
                user_agent=user_agent,
                success=False,
                details=details
            )

        log_security_event(
            "auth.login.failed",
            user_id=str(user.id),
            ip_address=client_ip,
            user_agent=user_agent,
            success=False,
            details=details
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # 5. Check if user account is deactivated
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # 6. Reset failed attempts counter on successful password verification
    user.failed_login_attempts = 0
    user.locked_until = None

    # Transparently upgrade legacy bcrypt hash to Argon2id
    if new_argon2_hash:
        user.hashed_password = new_argon2_hash

    # 7. Check if Multi-Factor Authentication is active
    if user.mfa_enabled and user.mfa_secret:
        mfa_ticket = create_mfa_ticket(str(user.id))
        await db.commit()
        log_security_event(
            "auth.mfa.required",
            user_id=str(user.id),
            ip_address=client_ip,
            user_agent=user_agent,
            success=True
        )
        return AuthResponse(
            mfa_required=True,
            mfa_ticket=mfa_ticket,
            message="Please provide your 2FA authenticator or backup code to complete sign in.",
        )

    # 8. Complete standard login: create session and issue tokens
    session_id = uuid.uuid4()
    family_id = uuid.uuid4()
    access_token = create_access_token(data={"sub": str(user.id), "session_id": str(session_id)})
    refresh_token = create_refresh_token(
        user_id=str(user.id),
        session_id=str(session_id),
        family_id=str(family_id)
    )

    session_rec = UserSession(
        id=session_id,
        user_id=user.id,
        refresh_token_hash=hash_token(refresh_token),
        family_id=family_id,
        ip_address=client_ip,
        user_agent=user_agent,
        expires_at=now_utc.replace(tzinfo=None) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(session_rec)
    user.update_last_active()
    await db.commit()

    # Set hardened HttpOnly cookies
    set_auth_cookies(response, access_token=access_token, refresh_token=refresh_token)

    log_security_event(
        "auth.login.success",
        user_id=str(user.id),
        ip_address=client_ip,
        user_agent=user_agent,
        success=True
    )

    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


# ==============================================================================
# 3. Multi-Factor Authentication (MFA / 2FA) Verification & Management
# ==============================================================================

@router.post(
    "/mfa/verify",
    response_model=AuthResponse,
    summary="Complete login via TOTP or single-use backup code",
)
@limiter.limit("10/minute")
async def verify_mfa(
    request: Request,
    response: Response,
    payload: MfaVerifyRequest,
    db: AsyncSession = Depends(get_db)
) -> AuthResponse:
    """Validate 6-digit TOTP code or backup code to complete sign in."""
    client_ip = _get_client_ip(request)
    user_agent = _get_user_agent(request)
    now_utc = datetime.now(timezone.utc)

    # 1. Validate intermediate MFA ticket
    token_payload = decode_access_token(payload.mfa_ticket, expected_type="mfa_pending")
    user_id = token_payload["sub"]

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active or not user.mfa_enabled or not user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA session",
        )

    # 2. Check 6-digit TOTP code
    is_valid_totp = verify_totp_code(user.mfa_secret, payload.code)
    used_backup_code = False

    if not is_valid_totp and user.mfa_backup_codes:
        # Check single-use backup code
        is_backup_valid, remaining_codes = verify_and_consume_backup_code(
            payload.code,
            user.mfa_backup_codes
        )
        if is_backup_valid:
            used_backup_code = True
            user.mfa_backup_codes = remaining_codes

    if not is_valid_totp and not used_backup_code:
        log_security_event(
            "auth.mfa.failed",
            user_id=str(user.id),
            ip_address=client_ip,
            user_agent=user_agent,
            success=False
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid verification code. Please check your authenticator app or backup code.",
        )

    # 3. Create active session and issue tokens
    session_id = uuid.uuid4()
    family_id = uuid.uuid4()
    access_token = create_access_token(data={"sub": str(user.id), "session_id": str(session_id)})
    refresh_token = create_refresh_token(
        user_id=str(user.id),
        session_id=str(session_id),
        family_id=str(family_id)
    )

    session_rec = UserSession(
        id=session_id,
        user_id=user.id,
        refresh_token_hash=hash_token(refresh_token),
        family_id=family_id,
        ip_address=client_ip,
        user_agent=user_agent,
        expires_at=now_utc.replace(tzinfo=None) + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(session_rec)
    user.update_last_active()
    await db.commit()

    set_auth_cookies(response, access_token=access_token, refresh_token=refresh_token)

    log_security_event(
        "auth.mfa.success",
        user_id=str(user.id),
        ip_address=client_ip,
        user_agent=user_agent,
        success=True,
        details={"used_backup_code": used_backup_code}
    )

    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/mfa/setup",
    response_model=MfaSetupResponse,
    summary="Begin TOTP setup: returns secret and QR code",
)
async def setup_mfa(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> MfaSetupResponse:
    """Generate TOTP secret and QR code URI for authenticator app configuration."""
    result = await db.execute(select(User).where(User.id == uuid.UUID(current_user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    secret = generate_totp_secret()
    provisioning_uri = generate_provisioning_uri(user.email or user.name, secret)
    qr_data_uri = generate_qr_code_base64(provisioning_uri)

    return MfaSetupResponse(
        secret=secret,
        provisioning_uri=provisioning_uri,
        qr_code_data_uri=qr_data_uri,
    )


@router.post(
    "/mfa/activate",
    response_model=MfaActivateResponse,
    summary="Confirm TOTP code and enable MFA",
)
async def activate_mfa(
    payload: MfaActivateRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> MfaActivateResponse:
    """Verify first TOTP code and activate MFA, generating 10 recovery codes."""
    result = await db.execute(select(User).where(User.id == uuid.UUID(current_user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    is_valid = verify_totp_code(payload.secret, payload.code)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid confirmation code. Please verify your device clock is synchronized and try again.",
        )

    # Generate 10 single-use recovery codes
    plain_codes, hashed_codes = generate_backup_codes(count=10)

    user.mfa_secret = payload.secret
    user.mfa_enabled = True
    user.mfa_backup_codes = hashed_codes
    await db.commit()

    log_security_event(
        "auth.mfa.activated",
        user_id=str(user.id),
        success=True
    )

    return MfaActivateResponse(
        message="MFA has been successfully activated on your account.",
        mfa_enabled=True,
        backup_codes=plain_codes,
    )


@router.post(
    "/mfa/disable",
    summary="Disable MFA on user account",
)
async def disable_mfa(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Disable TOTP MFA on account."""
    result = await db.execute(select(User).where(User.id == uuid.UUID(current_user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.mfa_enabled = False
    user.mfa_secret = None
    user.mfa_backup_codes = []
    await db.commit()

    log_security_event(
        "auth.mfa.disabled",
        user_id=str(user.id),
        success=True
    )
    return {"message": "Two-factor authentication has been disabled."}


# ==============================================================================
# 4. Refresh Token Rotation (RTR) & Session Revocation
# ==============================================================================

@router.post(
    "/refresh",
    summary="Rotate refresh token and issue new access token",
)
async def refresh_tokens(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Execute Refresh Token Rotation with automatic theft/reuse detection."""
    client_ip = _get_client_ip(request)
    user_agent = _get_user_agent(request)
    now_utc = datetime.now(timezone.utc)

    # 1. Extract refresh token from HttpOnly cookie or Authorization header
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            refresh_token = auth_header.split(" ", 1)[1]

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
        )

    # 2. Decode and validate refresh token structure
    payload = decode_access_token(refresh_token, expected_type="refresh")
    user_id = uuid.UUID(payload["sub"])
    session_id = uuid.UUID(payload["session_id"])
    family_id = uuid.UUID(payload["family_id"])
    token_h = hash_token(refresh_token)

    # 3. Retrieve session record
    res = await db.execute(select(UserSession).where(UserSession.id == session_id))
    session = res.scalar_one_or_none()

    # 4. Token Reuse Detection
    # If session doesn't exist, is revoked, or token hash does not match current hash:
    if not session or session.is_revoked or session.refresh_token_hash != token_h:
        # Breached! Replay attack detected. Revoke ALL sessions in this family immediately!
        await db.execute(
            update(UserSession)
            .where(UserSession.family_id == family_id)
            .values(is_revoked=True)
        )
        await db.commit()
        clear_auth_cookies(response)

        log_security_event(
            "auth.token.reuse_detected",
            user_id=str(user_id),
            ip_address=client_ip,
            user_agent=user_agent,
            success=False,
            details={"family_id": str(family_id)}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Security breach detected: refresh token reuse. All active sessions have been terminated.",
        )

    # 5. Mint new Access Token and new Refresh Token (Rotation)
    new_access_token = create_access_token(data={"sub": str(user_id), "session_id": str(session_id)})
    new_refresh_token = create_refresh_token(
        user_id=str(user_id),
        session_id=str(session_id),
        family_id=str(family_id)
    )

    # 6. Update session record with new token hash
    session.refresh_token_hash = hash_token(new_refresh_token)
    session.expires_at = now_utc.replace(tzinfo=None) + timedelta(days=settings.refresh_token_expire_days)
    await db.commit()

    # 7. Set updated cookies
    set_auth_cookies(response, access_token=new_access_token, refresh_token=new_refresh_token)

    log_security_event(
        "auth.token.refreshed",
        user_id=str(user_id),
        ip_address=client_ip,
        user_agent=user_agent,
        success=True
    )

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
    }


@router.post(
    "/logout",
    summary="Log out of current session and revoke refresh token",
)
async def logout(
    request: Request,
    response: Response,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Revoke current session and clear authentication cookies."""
    client_ip = _get_client_ip(request)
    user_agent = _get_user_agent(request)

    # Extract session_id if available from access token
    token = request.cookies.get("access_token") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if token:
        try:
            payload = decode_access_token(token, expected_type="access")
            sid = payload.get("session_id")
            if sid:
                await db.execute(
                    update(UserSession)
                    .where(UserSession.id == uuid.UUID(sid))
                    .values(is_revoked=True)
                )
                await db.commit()
        except Exception:
            pass

    clear_auth_cookies(response)
    log_security_event(
        "auth.logout",
        user_id=current_user_id,
        ip_address=client_ip,
        user_agent=user_agent,
        success=True
    )
    return {"message": "Logged out successfully"}


@router.post(
    "/logout-all",
    summary="Log out of all devices and terminate all active sessions",
)
async def logout_all(
    response: Response,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Revoke all active sessions for current user."""
    await db.execute(
        update(UserSession)
        .where(UserSession.user_id == uuid.UUID(current_user_id))
        .values(is_revoked=True)
    )
    await db.commit()
    clear_auth_cookies(response)

    log_security_event(
        "auth.logout_all",
        user_id=current_user_id,
        success=True
    )
    return {"message": "All active sessions have been terminated."}


# ==============================================================================
# 5. User Profile & Active Session Inspection
# ==============================================================================

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get currently authenticated user profile",
)
async def get_me(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """Retrieve profile and 2FA status for the currently authenticated user."""
    result = await db.execute(select(User).where(User.id == uuid.UUID(current_user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)


@router.get(
    "/sessions",
    response_model=List[SessionResponse],
    summary="List active sessions/devices for user",
)
async def get_active_sessions(
    request: Request,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
) -> List[SessionResponse]:
    """List all non-revoked active sessions for device management."""
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    result = await db.execute(
        select(UserSession).where(
            UserSession.user_id == uuid.UUID(current_user_id),
            UserSession.is_revoked == False,
            UserSession.expires_at > now_naive,
        )
    )
    sessions = result.scalars().all()

    # Determine current session if token includes session_id
    current_sid = None
    token = request.cookies.get("access_token") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if token:
        try:
            payload = decode_access_token(token, expected_type="access")
            current_sid = payload.get("session_id")
        except Exception:
            pass

    out: List[SessionResponse] = []
    for s in sessions:
        out.append(SessionResponse(
            id=s.id,
            ip_address=s.ip_address,
            user_agent=s.user_agent,
            is_current=(str(s.id) == current_sid),
            created_at=s.created_at,
            expires_at=s.expires_at,
        ))
    return out
