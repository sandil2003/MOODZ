"""Cryptographic utilities for password hashing, legacy migration, and NIST SP 800-63B compliance.

Supports Argon2id (OWASP recommended) with automatic migration of legacy bcrypt hashes,
timing-attack-safe dummy verification, and breached password detection via HIBP k-Anonymity.
"""

import hashlib
import re
import secrets
from typing import Tuple, Optional, List
import bcrypt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
import httpx

from config import settings

# Initialize Argon2id hasher with OWASP recommended parameters
# Memory: 64MB (65536 KiB), Time: 3 iterations, Parallelism: 4 threads
_argon2_hasher = Argon2Hasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
)
password_hash = PasswordHash((_argon2_hasher,))

# Pre-computed dummy Argon2id hash for constant-time email enumeration defense
DUMMY_ARGON2_HASH = password_hash.hash("DummyPasswordVerificationForTimingDefense123!")

# Common weak and compromised passwords blocklist (subset of top breached passwords)
TOP_COMPROMISED_PASSWORDS = {
    "password", "password123", "12345678", "123456789", "qwerty123",
    "iloveyou", "admin123", "welcome1", "monkey123", "dragon123",
    "master123", "sunshine1", "princess1", "football1", "shadow123",
    "trustno1", "letmein1", "starwars", "chelsea1", "liverpool"
}


def hash_password(password: str) -> str:
    """Hash a plain-text password using Argon2id."""
    return password_hash.hash(password)


def verify_and_update_password(plain_password: str, hashed_password: str) -> Tuple[bool, Optional[str]]:
    """Verify a plain-text password against a hash, supporting transparent migration.

    Returns:
        (is_valid, new_hash_if_migrated):
        - If verified with legacy bcrypt ($2b$ or $2a$), computes and returns new Argon2id hash.
        - If verified with Argon2id, returns (True, None).
        - If invalid, returns (False, None).
    """
    if not plain_password or not hashed_password:
        return False, None

    # 1. Check if hash is legacy bcrypt
    if hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$"):
        try:
            is_valid = bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed_password.encode("utf-8")
            )
            if is_valid:
                # Transparently migrate to Argon2id
                new_argon2_hash = hash_password(plain_password)
                return True, new_argon2_hash
            return False, None
        except Exception:
            return False, None

    # 2. Verify with Argon2id
    try:
        is_valid = password_hash.verify(plain_password, hashed_password)
        return is_valid, None
    except Exception:
        return False, None


def verify_dummy_password() -> None:
    """Execute constant-time dummy verification when user is not found.
    Neutralizes email enumeration via timing side-channel analysis.
    """
    try:
        password_hash.verify("NonExistentPasswordAttempt", DUMMY_ARGON2_HASH)
    except Exception:
        pass


async def check_have_i_been_pwned(password: str) -> bool:
    """Check if password has appeared in known data breaches using HIBP k-Anonymity API.
    
    Safe & Zero Knowledge: Only the first 5 hexadecimal characters of the SHA-1 hash
    are transmitted over HTTPS. The rest of the hash remains strictly on the server.
    """
    if not settings.hibp_check_enabled:
        return False

    sha1_hash = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    prefix = sha1_hash[:5]
    suffix = sha1_hash[5:]

    url = f"https://api.pwnedpasswords.com/range/{prefix}"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(url, headers={"User-Agent": "MOODZ-Security-Audit"})
            if resp.status_code == 200:
                for line in resp.text.splitlines():
                    parts = line.split(":")
                    if parts[0].strip().upper() == suffix:
                        return True  # Found in breach
    except Exception:
        # Fall back gracefully if external HIBP API is unreachable or rate limited
        pass

    return False


async def validate_password_strength(password: str, user_inputs: Optional[List[str]] = None) -> Tuple[bool, Optional[str]]:
    """Validate password according to NIST SP 800-63B standards.

    - Length: Minimum 10 characters, maximum 128 characters.
    - All Unicode characters allowed (including spaces, symbols, emojis).
    - No artificial composition rules (e.g. forcing 1 uppercase, 1 symbol) per NIST guidance.
    - Checks against top compromised passwords dictionary.
    - Checks against HaveIBeenPwned k-anonymity API.
    - Checks that password does not contain identifiable user inputs (e.g. name or email username).
    """
    if len(password) < 10:
        return False, "Password must be at least 10 characters long per NIST SP 800-63B guidelines."

    if len(password) > 128:
        return False, "Password cannot exceed 128 characters."

    # Check against local compromised passwords list
    pw_lower = password.lower().strip()
    if pw_lower in TOP_COMPROMISED_PASSWORDS:
        return False, "This password is known to be commonly used and insecure. Please choose a more unique phrase."

    # Check for sequential / repetitive patterns
    if re.search(r"(.)\1{4,}", password):
        return False, "Password contains excessive repeating characters."

    # Check against user context (name, email)
    if user_inputs:
        for inp in user_inputs:
            if inp:
                words = re.split(r"[\s@._-]+", inp.strip())
                for w in [inp] + words:
                    w_clean = re.sub(r"[^a-zA-Z0-9]", "", w).lower()
                    if len(w_clean) >= 3 and w_clean in pw_lower:
                        return False, "Password should not contain your personal information (name or email)."

    # Check breached passwords database
    is_breached = await check_have_i_been_pwned(password)
    if is_breached:
        return False, "This password has appeared in known security breaches. Please choose a different password."

    return True, None
