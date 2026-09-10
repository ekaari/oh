import base64
import hashlib
import os

from cryptography.fernet import Fernet

from app.core.config import settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.secret_key.encode()).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_secret(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()


SENSITIVE_KEYS = {
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "credential",
}


def mask_sensitive(value: str | None, visible: int = 2) -> str:
    if not value:
        return ""
    if len(value) <= visible * 2:
        return "*" * len(value)
    return f"{value[:visible]}{'*' * (len(value) - visible * 2)}{value[-visible:]}"


def sanitize_for_prompt(text: str) -> str:
    """Strip likely secrets before sending text to an LLM."""
    lowered = text.lower()
    for key in SENSITIVE_KEYS:
        if key in lowered:
            return "[REDACTED_SENSITIVE_CONTENT]"
    return text


def generate_id(prefix: str) -> str:
    return f"{prefix}-{os.urandom(4).hex()}"
