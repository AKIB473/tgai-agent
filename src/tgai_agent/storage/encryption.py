"""
storage/encryption.py — AES-256 (Fernet) symmetric encryption for sensitive fields.

All API keys and session secrets are stored encrypted at rest.
The ENCRYPTION_KEY env var must be a valid Fernet key (32-byte base64url).

Generate a key:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from tgai_agent.config import settings
from tgai_agent.utils.logger import get_logger

log = get_logger(__name__)

_fernet: Fernet | None = None
_fernet_key: str | None = None


def _get_fernet() -> Fernet:
    global _fernet, _fernet_key
    current_key = settings.encryption_key
    if _fernet is None or _fernet_key != current_key:
        _fernet_key = current_key
        _fernet = Fernet(current_key.encode())
    return _fernet


def encrypt(plaintext: str) -> str:
    """Encrypt a string and return a base64-encoded ciphertext string."""
    if not plaintext:
        return ""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """
    Decrypt a Fernet ciphertext string.
    Returns empty string if ciphertext is empty or decryption fails.
    """
    if not ciphertext:
        return ""
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        log.error("encryption.decrypt_failed", hint="Key mismatch or corrupted data")
        return ""
