"""Multi-Factor Authentication (MFA) service implementing TOTP (RFC 6238) and backup codes."""

import base64
import hashlib
import io
import secrets
from typing import List, Tuple, Optional

import pyotp
import qrcode
from qrcode.image.pil import PilImage


def generate_totp_secret() -> str:
    """Generate a high-entropy base32 secret key for TOTP."""
    return pyotp.random_base32()


def generate_provisioning_uri(user_email: str, secret: str, app_name: str = "MOODZ") -> str:
    """Generate the standard otpauth:// URI for authenticator applications."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=user_email, issuer_name=app_name)


def generate_qr_code_base64(provisioning_uri: str) -> str:
    """Generate a base64-encoded PNG data URI of the QR code for UI rendering."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(provisioning_uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64_png = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_png}"


def verify_totp_code(secret: str, code: str, valid_window: int = 1) -> bool:
    """Verify a 6-digit TOTP code against the user's secret.
    
    valid_window=1 allows +-30 seconds of clock drift tolerance.
    """
    if not secret or not code:
        return False

    totp = pyotp.TOTP(secret)
    # Strip spaces or hyphens if user typed "123 456"
    sanitized_code = code.replace(" ", "").replace("-", "").strip()
    return bool(totp.verify(sanitized_code, valid_window=valid_window))


def _hash_backup_code(plain_code: str) -> str:
    """Hash single-use recovery code with SHA-256 for secure storage."""
    return hashlib.sha256(plain_code.strip().encode("utf-8")).hexdigest()


def generate_backup_codes(count: int = 10) -> Tuple[List[str], List[str]]:
    """Generate single-use backup recovery codes.
    
    Returns:
        (plain_codes, hashed_codes):
        - plain_codes: Shown to the user ONCE to download/save. Formatted as 'xxxx-xxxx'.
        - hashed_codes: Stored securely in database.
    """
    plain_codes: List[str] = []
    hashed_codes: List[str] = []

    for _ in range(count):
        part1 = secrets.token_hex(2).upper()
        part2 = secrets.token_hex(2).upper()
        code = f"{part1}-{part2}"
        plain_codes.append(code)
        hashed_codes.append(_hash_backup_code(code))

    return plain_codes, hashed_codes


def verify_and_consume_backup_code(
    plain_code: str,
    hashed_codes: List[str]
) -> Tuple[bool, List[str]]:
    """Verify a single-use backup code against stored hashes and burn it.

    Returns:
        (is_valid, remaining_hashed_codes)
    """
    if not plain_code or not hashed_codes:
        return False, hashed_codes

    code_hash = _hash_backup_code(plain_code)
    if code_hash in hashed_codes:
        # Code matched: burn it by returning remaining codes
        remaining = [h for h in hashed_codes if h != code_hash]
        return True, remaining

    return False, hashed_codes
