"""Tests for Fernet encryption/decryption round-trip and error handling."""

import pytest
from cryptography.fernet import Fernet

from src.core.encryption import EncryptionError, EncryptionService


class TestEncryptionService:
    """Tests for the EncryptionService class."""

    @pytest.fixture
    def valid_key(self) -> str:
        """Generate a valid Fernet key for testing."""
        return Fernet.generate_key().decode()

    @pytest.fixture
    def encryption_service(self, valid_key: str) -> EncryptionService:
        """Create an EncryptionService with a valid key."""
        return EncryptionService(valid_key)

    def test_encrypt_decrypt_round_trip(self, encryption_service: EncryptionService):
        """Encrypting then decrypting must return the original plaintext."""
        plaintext = b"Sensitive document content for verification"
        ciphertext = encryption_service.encrypt(plaintext)
        assert ciphertext != plaintext
        assert encryption_service.decrypt(ciphertext) == plaintext

    def test_encrypt_decrypt_empty_bytes(self, encryption_service: EncryptionService):
        """Empty byte strings must round-trip correctly."""
        plaintext = b""
        ciphertext = encryption_service.encrypt(plaintext)
        assert encryption_service.decrypt(ciphertext) == plaintext

    def test_encrypt_decrypt_large_payload(self, encryption_service: EncryptionService):
        """A 10 MB payload (max document size) must round-trip."""
        plaintext = b"A" * (10 * 1024 * 1024)
        ciphertext = encryption_service.encrypt(plaintext)
        assert encryption_service.decrypt(ciphertext) == plaintext

    def test_ciphertext_differs_across_calls(self, encryption_service: EncryptionService):
        """Fernet uses random IVs, so encrypting the same data twice
        must produce different ciphertext."""
        plaintext = b"test data"
        ct1 = encryption_service.encrypt(plaintext)
        ct2 = encryption_service.encrypt(plaintext)
        assert ct1 != ct2

    def test_decrypt_with_wrong_key_raises(self, valid_key: str):
        """Decrypting with a different key must raise EncryptionError."""
        service1 = EncryptionService(valid_key)
        service2 = EncryptionService(Fernet.generate_key().decode())

        ciphertext = service1.encrypt(b"secret")
        with pytest.raises(EncryptionError, match="invalid token or wrong key"):
            service2.decrypt(ciphertext)

    def test_decrypt_corrupted_token_raises(self, encryption_service: EncryptionService):
        """Corrupted ciphertext must raise EncryptionError."""
        with pytest.raises(EncryptionError):
            encryption_service.decrypt(b"not-a-valid-fernet-token")

    def test_empty_key_raises(self):
        """An empty encryption key must raise EncryptionError."""
        with pytest.raises(EncryptionError, match="not configured"):
            EncryptionService("")

    def test_invalid_key_format_raises(self):
        """A key that is not valid base64 must raise EncryptionError."""
        with pytest.raises(EncryptionError, match="Invalid encryption key"):
            EncryptionService("not-a-valid-fernet-key")

    def test_binary_data_round_trip(self, encryption_service: EncryptionService):
        """Binary data (e.g. PDF magic bytes) must survive round-trip."""
        pdf_header = b"%PDF-1.4 binary\x00\xff\xfe content"
        ciphertext = encryption_service.encrypt(pdf_header)
        assert encryption_service.decrypt(ciphertext) == pdf_header
