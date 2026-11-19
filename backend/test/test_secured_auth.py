"""Automated security verification test suite for the new secured login architecture:
1. Argon2id cryptographic hashing & seamless legacy bcrypt migration
2. NIST SP 800-63B password strength validation & HIBP check
3. Anti-brute-force rate limiting, failed attempt counter, and account lockout
4. TOTP MFA setup, verification, and single-use backup code consumption
5. Refresh Token Rotation (RTR) and token reuse detection (family revocation)
6. HttpOnly cookie authentication extraction
"""

import os
import sys
import uuid
import time
import pytest
import sqlite3
from datetime import datetime, timedelta, timezone

sqlite3.register_adapter(uuid.UUID, lambda u: u.hex)
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from config import settings
from app.models import Base, User, UserSession
from app.core import database as app_db
from app.core.security_crypto import (
    hash_password,
    verify_and_update_password,
    validate_password_strength,
)
from app.core.mfa_service import (
    generate_totp_secret,
    generate_provisioning_uri,
    generate_qr_code_base64,
    verify_totp_code,
    generate_backup_codes,
    verify_and_consume_backup_code,
)
from app.core.auth_utils import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_token,
    set_auth_cookies,
    clear_auth_cookies,
)
from main import app as fastapi_app
import bcrypt
import pyotp


@pytest.fixture
async def auth_test_env():
    """Isolated test environment with in-memory SQLite and seeded test accounts."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    orig_async_session_local = app_db.AsyncSessionLocal
    app_db.AsyncSessionLocal = TestSessionLocal

    async def override_get_db():
        async with TestSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    fastapi_app.dependency_overrides[app_db.get_db] = override_get_db

    # Seed User 1: Modern Argon2id user
    user1_id = uuid.uuid4()
    # Seed User 2: Legacy bcrypt user for migration testing
    user2_id = uuid.uuid4()
    # Seed User 3: MFA-enabled user
    user3_id = uuid.uuid4()
    totp_secret = generate_totp_secret()
    _, backup_code_hashes = generate_backup_codes(count=5)

    legacy_bcrypt_pw = "LegacyBcryptPassword123!"
    salt = bcrypt.gensalt()
    legacy_hash = bcrypt.hashpw(legacy_bcrypt_pw.encode("utf-8"), salt).decode("utf-8")

    async with TestSessionLocal() as db:
        user_argon = User(
            id=user1_id,
            name="Modern Argon User",
            email="argon.user@moodz.ai",
            hashed_password=hash_password("ArgonSecurePassword123!"),
            role="user",
            is_active=True,
            failed_login_attempts=0,
            mfa_enabled=False,
        )
        user_legacy = User(
            id=user2_id,
            name="Legacy Bcrypt User",
            email="legacy.user@moodz.ai",
            hashed_password=legacy_hash,
            role="user",
            is_active=True,
            failed_login_attempts=0,
            mfa_enabled=False,
        )
        user_mfa = User(
            id=user3_id,
            name="MFA Protected User",
            email="mfa.user@moodz.ai",
            hashed_password=hash_password("MfaPasswordProtected123!"),
            role="user",
            is_active=True,
            mfa_enabled=True,
            mfa_secret=totp_secret,
            mfa_backup_codes=backup_code_hashes,
            failed_login_attempts=0,
        )
        db.add_all([user_argon, user_legacy, user_mfa])
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as client:
        yield {
            "client": client,
            "session_factory": TestSessionLocal,
            "user1_id": user1_id,
            "user2_id": user2_id,
            "user3_id": user3_id,
            "totp_secret": totp_secret,
            "legacy_pw": legacy_bcrypt_pw,
        }

    fastapi_app.dependency_overrides.clear()
    app_db.AsyncSessionLocal = orig_async_session_local
    await engine.dispose()


# ==============================================================================
# Unit Tests
# ==============================================================================

def test_01_argon2id_hashing_and_verification():
    """Verify Argon2id cryptographic parameters and signature."""
    raw_pw = "MentalWellnessPrivacy2026!"
    hashed = hash_password(raw_pw)

    # Argon2id signature check
    assert hashed.startswith("$argon2id$")
    assert "m=65536" in hashed
    assert "t=3" in hashed
    assert "p=4" in hashed

    # Valid and invalid checks
    is_valid, _ = verify_and_update_password(raw_pw, hashed)
    assert is_valid is True

    is_invalid, _ = verify_and_update_password("WrongPassword!", hashed)
    assert is_invalid is False


def test_02_transparent_legacy_bcrypt_migration():
    """Verify that legacy bcrypt hashes verify and automatically upgrade to Argon2id."""
    raw_pw = "OldBcryptPassword2024!"
    salt = bcrypt.gensalt()
    bcrypt_hash = bcrypt.hashpw(raw_pw.encode("utf-8"), salt).decode("utf-8")
    assert bcrypt_hash.startswith("$2b$")

    # Verification must succeed AND provide a new Argon2id hash
    is_valid, new_hash = verify_and_update_password(raw_pw, bcrypt_hash)
    assert is_valid is True
    assert new_hash is not None
    assert new_hash.startswith("$argon2id$")

    # Newly generated Argon2id hash must verify with the same password
    assert verify_and_update_password(raw_pw, new_hash)[0] is True


@pytest.mark.asyncio
async def test_03_nist_password_strength_validation():
    """Verify NIST SP 800-63B password rules (length, compromised list, no arbitrary composition)."""
    # 1. Too short (< 10 chars)
    valid, msg = await validate_password_strength("short")
    assert not valid
    assert "at least 10 characters" in msg

    # 2. Top compromised password
    valid, msg = await validate_password_strength("password123")
    assert not valid
    assert "commonly used" in msg

    # 3. Excessive repeating characters
    valid, msg = await validate_password_strength("aaaaaaabbbbbb")
    assert not valid

    # 4. Contains user personal context
    valid, msg = await validate_password_strength("alexsmithpassphrase", user_inputs=["Alex Smith"])
    assert not valid
    assert "personal information" in msg

    # 5. Strong passphrase without arbitrary symbol rules
    valid, msg = await validate_password_strength("correct horse battery staple wellness")
    assert valid is True
    assert msg is None


def test_04_mfa_totp_and_backup_codes():
    """Verify RFC 6238 TOTP generation/verification and single-use backup code consumption."""
    secret = generate_totp_secret()
    totp = pyotp.TOTP(secret)
    current_code = totp.now()

    # Valid TOTP code
    assert verify_totp_code(secret, current_code) is True
    # Invalid TOTP code
    assert verify_totp_code(secret, "000000") is False

    # Provisioning URI and QR code
    uri = generate_provisioning_uri("user@moodz.ai", secret)
    assert "otpauth://totp/MOODZ:" in uri
    assert "secret=" in uri

    qr = generate_qr_code_base64(uri)
    assert qr.startswith("data:image/png;base64,")

    # Backup recovery codes
    plain_codes, hashed_codes = generate_backup_codes(count=5)
    assert len(plain_codes) == 5
    assert len(hashed_codes) == 5

    test_code = plain_codes[0]
    is_valid, remaining = verify_and_consume_backup_code(test_code, hashed_codes)
    assert is_valid is True
    assert len(remaining) == 4

    # Consuming the same code again must fail (single-use burned!)
    is_valid_again, _ = verify_and_consume_backup_code(test_code, remaining)
    assert is_valid_again is False


@pytest.mark.asyncio
async def test_05_login_success_and_httponly_cookies(auth_test_env):
    """Verify successful login sets HttpOnly cookies and returns AuthResponse."""
    client = auth_test_env["client"]

    resp = await client.post(
        "/api/auth/login",
        json={"email": "argon.user@moodz.ai", "password": "ArgonSecurePassword123!"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "argon.user@moodz.ai"
    assert data["mfa_required"] is False

    # Check HttpOnly cookies in response headers
    set_cookie_headers = resp.headers.get_list("set-cookie")
    cookie_str = "; ".join(set_cookie_headers)
    assert "access_token=" in cookie_str
    assert "refresh_token=" in cookie_str
    assert "HttpOnly" in cookie_str
    assert "SameSite=lax" in cookie_str


@pytest.mark.asyncio
async def test_06_login_transparent_bcrypt_migration(auth_test_env):
    """Verify that logging in with legacy bcrypt transparently upgrades DB hash to Argon2id."""
    client = auth_test_env["client"]
    session_factory = auth_test_env["session_factory"]

    resp = await client.post(
        "/api/auth/login",
        json={"email": "legacy.user@moodz.ai", "password": auth_test_env["legacy_pw"]}
    )
    assert resp.status_code == 200

    # Query DB to inspect updated hash
    async with session_factory() as db:
        res = await db.execute(select(User).where(User.id == auth_test_env["user2_id"]))
        user = res.scalar_one()
        assert user.hashed_password.startswith("$argon2id$")


@pytest.mark.asyncio
async def test_07_brute_force_lockout_enforcement(auth_test_env):
    """Verify 5 failed attempts trigger account lockout (HTTP 423 Locked)."""
    client = auth_test_env["client"]

    # Dispatch 5 incorrect password attempts
    for i in range(5):
        resp = await client.post(
            "/api/auth/login",
            json={"email": "argon.user@moodz.ai", "password": f"WrongAttempt{i}!"}
        )
        assert resp.status_code == 401
        assert "Invalid email or password" in resp.json()["detail"]

    # 6th attempt must be rejected with 423 Locked
    resp_locked = await client.post(
        "/api/auth/login",
        json={"email": "argon.user@moodz.ai", "password": "ArgonSecurePassword123!"}
    )
    assert resp_locked.status_code == 423
    assert "Account is temporarily locked" in resp_locked.json()["detail"]


@pytest.mark.asyncio
async def test_08_mfa_login_challenge_flow(auth_test_env):
    """Verify two-step MFA challenge and verification flow."""
    client = auth_test_env["client"]

    # Step 1: Login with password triggers mfa_required
    resp1 = await client.post(
        "/api/auth/login",
        json={"email": "mfa.user@moodz.ai", "password": "MfaPasswordProtected123!"}
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["mfa_required"] is True
    assert "mfa_ticket" in data1
    assert data1["access_token"] is None

    ticket = data1["mfa_ticket"]

    # Step 2: Submit invalid TOTP code
    resp_bad_mfa = await client.post(
        "/api/auth/mfa/verify",
        json={"mfa_ticket": ticket, "code": "000000"}
    )
    assert resp_bad_mfa.status_code == 401

    # Step 3: Submit valid TOTP code
    totp = pyotp.TOTP(auth_test_env["totp_secret"])
    valid_code = totp.now()

    resp_good_mfa = await client.post(
        "/api/auth/mfa/verify",
        json={"mfa_ticket": ticket, "code": valid_code}
    )
    assert resp_good_mfa.status_code == 200
    data_good = resp_good_mfa.json()
    assert data_good["access_token"] is not None
    assert data_good["user"]["email"] == "mfa.user@moodz.ai"


@pytest.mark.asyncio
async def test_09_refresh_token_rotation_and_theft_detection(auth_test_env):
    """Verify Refresh Token Rotation (RTR) and automatic family revocation upon reuse."""
    client = auth_test_env["client"]

    # 1. Login to obtain initial tokens
    login_resp = await client.post(
        "/api/auth/login",
        json={"email": "argon.user@moodz.ai", "password": "ArgonSecurePassword123!"}
    )
    assert login_resp.status_code == 200

    # Extract initial refresh token from cookies
    initial_refresh_token = login_resp.cookies.get("refresh_token")
    assert initial_refresh_token is not None

    # 2. Rotate refresh token once
    rotate_resp1 = await client.post(
        "/api/auth/refresh",
        cookies={"refresh_token": initial_refresh_token}
    )
    assert rotate_resp1.status_code == 200
    new_access_token = rotate_resp1.json()["access_token"]
    new_refresh_token = rotate_resp1.cookies.get("refresh_token")
    assert new_refresh_token != initial_refresh_token

    # 3. Simulate REPLAY ATTACK: Replay the initial (already rotated) refresh token!
    replay_resp = await client.post(
        "/api/auth/refresh",
        cookies={"refresh_token": initial_refresh_token}
    )
    assert replay_resp.status_code == 401
    assert "token reuse" in replay_resp.json()["detail"].lower()

    # 4. Verify that the entire session family was revoked
    rotate_resp2 = await client.post(
        "/api/auth/refresh",
        cookies={"refresh_token": new_refresh_token}
    )
    assert rotate_resp2.status_code == 401
