"""Fernet-based encryption for user API keys."""

import base64
import hashlib

from cryptography.fernet import Fernet

from app.config import get_settings

_settings = get_settings()

# Derive a stable 32-byte Fernet key from SECRET_KEY via SHA-256
_raw = hashlib.sha256(_settings.SECRET_KEY.encode()).digest()
_fernet = Fernet(base64.urlsafe_b64encode(_raw))


def encrypt_api_key(plain_key: str) -> str:
    """Encrypt an API key and return the ciphertext as a UTF-8 string."""
    return _fernet.encrypt(plain_key.encode()).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt a stored API key ciphertext back to plaintext."""
    return _fernet.decrypt(encrypted_key.encode()).decode()


def mask_api_key(plain_key: str) -> str:
    """Return a masked version of an API key for display (e.g. sk-...abcd)."""
    if len(plain_key) <= 8:
        return "••••"
    return f"{plain_key[:4]}...{plain_key[-4:]}"
