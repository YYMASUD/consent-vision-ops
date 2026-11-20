"""Envelope encryption for sensitive at-rest fields (spec §18)."""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config.settings import get_settings

_PREFIX = "enc:v1:"


def _fernet() -> Fernet:
    """Derive a stable Fernet key from the configured secret."""
    settings = get_settings()
    secret = settings.encryption_key or settings.jwt_secret
    digest = hashlib.sha256(secret.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_str(value: str | None) -> str | None:
    """Encrypt a sensitive string for storage. Idempotent for already-encrypted values."""
    if value is None or value == "":
        return value
    if value.startswith(_PREFIX):
        return value
    token = _fernet().encrypt(value.encode()).decode()
    return f"{_PREFIX}{token}"


def decrypt_str(value: str | None) -> str | None:
    """Decrypt a stored value; returns input unchanged when not encrypted."""
    if value is None or value == "":
        return value
    if not value.startswith(_PREFIX):
        return value
    try:
        return _fernet().decrypt(value[len(_PREFIX) :].encode()).decode()
    except InvalidToken:
        return None


def redact(value: str | None) -> str | None:
    """Mask a credential for API responses (never return raw stream URLs)."""
    if not value:
        return value
    return "***redacted***"