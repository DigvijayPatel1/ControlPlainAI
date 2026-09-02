"""Security primitives for API-key authentication."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import hashlib
import hmac
import secrets
import bcrypt
import jwt

from app.core.config import settings

API_KEY_PREFIX = "cp_"
HASH_ALGORITHM = "sha256"
PBKDF2_ITERATIONS = 310_000


def generate_api_key(principal_id: str) -> tuple[str, str]:
    secret = secrets.token_urlsafe(32).replace("_", "-")
    raw_key = f"{API_KEY_PREFIX}{principal_id}_{secret}"
    return raw_key, hash_api_key(raw_key)


def hash_api_key(api_key: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(HASH_ALGORITHM, api_key.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_{HASH_ALGORITHM}${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def hash_secret(secret: str) -> str:
    """Compatibility alias for new API-key creation callers."""
    return hash_api_key(secret)


def verify_secret(secret: str, expected_hash: str) -> bool:
    return verify_api_key(secret, expected_hash)


def verify_api_key(api_key: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = stored_hash.split("$")
        if algorithm != f"pbkdf2_{HASH_ALGORITHM}":
            return False
        actual = hashlib.pbkdf2_hmac(
            HASH_ALGORITHM,
            api_key.encode(),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
        return hmac.compare_digest(actual, bytes.fromhex(digest_hex))
    except (TypeError, ValueError):
        return False


# ==================================================
# Password hashing (user accounts)
# ==================================================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"), 
        bcrypt.gensalt()
    ).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"), 
            hashed_password.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False


# ==================================================
# JWT access tokens (user sessions)
# ==================================================

def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.PyJWTError:
        return None