"""Password and session helpers. No secret values are logged."""

from __future__ import annotations

import hashlib
import hmac
import secrets

_ITERATIONS = 200_000
_DUMMY_HASH = (
    "pbkdf2_sha256$200000$"
    "00112233445566778899aabbccddeeff$"
    "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff"
)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations_text, salt_hex, digest_hex = stored.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_text)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (ValueError, TypeError):
        return False
    if iterations < 100_000 or iterations > 1_000_000:
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


def dummy_verify(password: str) -> None:
    """Spend a comparable hash when the account does not exist."""
    verify_password(password, _DUMMY_HASH)


def new_session_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    return token, hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
