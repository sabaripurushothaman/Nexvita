from werkzeug.security import (
    generate_password_hash as _generate_password_hash,
    check_password_hash as _check_password_hash
)
import secrets
import hashlib
import hmac
import base64
import os


def generate_password_hash(password: str) -> str:
    """Hash a plain-text password using werkzeug's secure hashing."""
    return _generate_password_hash(password)


def check_password_hash(pwhash: str, password: str) -> bool:
    """Verify a plain-text password against a stored hash."""
    return _check_password_hash(pwhash, password)


def generate_token(length: int = 32) -> str:
    """Generate a cryptographically secure URL-safe random token."""
    return secrets.token_urlsafe(length)


def verify_token(token: str, expected_token: str) -> bool:
    """
    Safely compare two tokens using constant-time comparison
    to prevent timing attacks.
    """
    if not token or not expected_token:
        return False
    return hmac.compare_digest(token.encode('utf-8'), expected_token.encode('utf-8'))


def hash_string(value: str) -> str:
    """Create a SHA-256 hash of a string value."""
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def generate_otp(length: int = 6) -> str:
    """Generate a numeric OTP of the given length."""
    digits = '0123456789'
    return ''.join(secrets.choice(digits) for _ in range(length))
