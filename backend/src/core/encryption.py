"""
Encryption Module

Provides symmetric encryption for sensitive documents stored at rest.
Uses Fernet (AES-128-CBC with HMAC-SHA256) from the ``cryptography`` library,
which is already present as a transitive dependency of ``python-jose[cryptography]``.

The encryption key is read from the DOCUMENT_ENCRYPTION_KEY environment variable.
Generate a key for local development with::

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

import logging
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Raised when encryption or decryption fails."""

    pass


class EncryptionService:
    """
    Thin wrapper around Fernet symmetric encryption.

    Each instance is bound to a single key, which must be a URL-safe
    base64-encoded 32-byte value (as produced by ``Fernet.generate_key()``).
    """

    def __init__(self, key: str) -> None:
        if not key:
            raise EncryptionError(
                "DOCUMENT_ENCRYPTION_KEY is not configured. "
                "Generate one with: python -c "
                '"from cryptography.fernet import Fernet; '
                'print(Fernet.generate_key().decode())"'
            )
        try:
            self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as exc:
            raise EncryptionError(
                f"Invalid encryption key format: {exc}"
            ) from exc

    def encrypt(self, data: bytes) -> bytes:
        """Encrypt *data* and return the Fernet token (ciphertext + HMAC)."""
        try:
            return self._fernet.encrypt(data)
        except Exception as exc:
            raise EncryptionError(f"Encryption failed: {exc}") from exc

    def decrypt(self, token: bytes) -> bytes:
        """Decrypt a Fernet *token* and return the original plaintext bytes."""
        try:
            return self._fernet.decrypt(token)
        except InvalidToken as exc:
            raise EncryptionError(
                "Decryption failed: invalid token or wrong key"
            ) from exc
        except Exception as exc:
            raise EncryptionError(f"Decryption failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Module-level singleton (configured at application startup)
# ---------------------------------------------------------------------------

_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """
    FastAPI dependency returning the configured EncryptionService singleton.

    Call ``configure_encryption_service`` at application startup.
    In tests, override this dependency directly.
    """
    if _encryption_service is None:
        raise RuntimeError(
            "Encryption service not configured. "
            "Call configure_encryption_service() at application startup."
        )
    return _encryption_service


def configure_encryption_service(key: str) -> None:
    """Set the global encryption service singleton (called once at startup)."""
    global _encryption_service
    _encryption_service = EncryptionService(key)
    logger.info("Encryption service configured successfully")
