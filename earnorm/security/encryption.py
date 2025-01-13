"""Encryption utilities for EarnORM."""

import base64
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class EncryptionManager:
    """Manager for field-level encryption."""

    def __init__(self) -> None:
        """Initialize encryption manager."""
        self._fernet = None
        self._default_key = None

    def _get_key(self, key: Optional[str] = None) -> bytes:
        """Get encryption key."""
        if key is None:
            if self._default_key is None:
                raise ValueError("No encryption key provided")
            return self._default_key

        # Generate key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"earnorm-salt",  # TODO: Make configurable
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(key.encode()))

    def _get_fernet(self, key: Optional[str] = None) -> Fernet:
        """Get Fernet instance."""
        if key is None and self._fernet is not None:
            return self._fernet

        key_bytes = self._get_key(key)
        return Fernet(key_bytes)

    async def encrypt(
        self,
        value: Any,
        key: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Encrypt value."""
        if value is None:
            return None

        # Convert value to string
        if not isinstance(value, str):
            value = str(value)

        # Get Fernet instance
        fernet = self._get_fernet(key)

        # Encrypt value
        encrypted = fernet.encrypt(value.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    async def decrypt(
        self,
        value: str,
        key: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Decrypt value."""
        if value is None:
            return None

        try:
            # Get Fernet instance
            fernet = self._get_fernet(key)

            # Decrypt value
            decrypted = fernet.decrypt(base64.urlsafe_b64decode(value.encode()))
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt value: {str(e)}")

    def set_default_key(self, key: str) -> None:
        """Set default encryption key."""
        self._default_key = self._get_key(key)
        self._fernet = self._get_fernet(key)
