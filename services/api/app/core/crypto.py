"""Token encryption using AES-GCM.

Provides encryption and decryption of OAuth tokens at rest.
Supports optional envelope encryption with GCP KMS (future enhancement).
"""
import base64
import os
import logging
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from app.config import agent_settings
from app.core.metrics import (
    crypto_decrypt_error_total,
    crypto_encrypt_total,
    crypto_decrypt_total,
    track_crypto_operation
)

logger = logging.getLogger(__name__)


class Crypto:
    """AES-GCM encryption for OAuth tokens.
    
    Encrypts tokens before storing in database and decrypts when reading.
    Uses a 256-bit AES key either from environment or ephemeral for dev.
    """
    
    def __init__(self):
        """Initialize crypto with AES-GCM cipher."""
        if not agent_settings.ENCRYPTION_ENABLED:
            self.aes = None
            logger.warning("Token encryption is DISABLED - tokens stored in plaintext")
            return
        
        if agent_settings.AES_KEY_BASE64:
            # Production: use key from environment
            try:
                key = base64.urlsafe_b64decode(agent_settings.AES_KEY_BASE64)
                if len(key) not in (16, 24, 32):
                    raise ValueError(f"AES key must be 128/192/256-bit, got {len(key)*8}-bit")
                logger.info(f"Loaded AES-{len(key)*8} key from environment")
            except Exception as e:
                logger.error(f"Failed to load AES key: {e}")
                raise ValueError("Invalid AES_KEY_BASE64 - must be valid base64 URL-safe encoded key")
        else:
            # Development: generate ephemeral key (warning: not persistent!)
            key = AESGCM.generate_key(bit_length=256)
            logger.warning("Using EPHEMERAL AES-256 key - tokens will be invalid after restart!")
        
        self.aes = AESGCM(key)
        logger.info("Token encryption initialized successfully")
    
    def enc(self, plaintext: bytes) -> bytes:
        """Encrypt plaintext bytes to base64-encoded ciphertext.
        
        Args:
            plaintext: Raw bytes to encrypt
            
        Returns:
            Base64 URL-safe encoded nonce + ciphertext
        """
        if not self.aes:
            # Encryption disabled - return plaintext
            return plaintext
        
        with track_crypto_operation("encrypt"):
            # Generate random 12-byte nonce (96 bits for GCM)
            nonce = os.urandom(12)
            
            # Encrypt with authenticated encryption (AEAD)
            ciphertext = self.aes.encrypt(nonce, plaintext, None)
            
            # Prepend nonce to ciphertext and encode
            result = base64.urlsafe_b64encode(nonce + ciphertext)
            crypto_encrypt_total.inc()
            return result
    
    def dec(self, blob: bytes) -> bytes:
        """Decrypt base64-encoded ciphertext to plaintext bytes.
        
        Args:
            blob: Base64 URL-safe encoded nonce + ciphertext
            
        Returns:
            Decrypted plaintext bytes
            
        Raises:
            InvalidTag: If ciphertext was tampered with
            ValueError: If blob is malformed
        """
        if not self.aes:
            # Encryption disabled - return blob as-is
            return blob
        
        with track_crypto_operation("decrypt"):
            # Decode base64
            try:
                raw = base64.urlsafe_b64decode(blob)
            except Exception as e:
                logger.error(f"Failed to decode encrypted blob: {e}")
                crypto_decrypt_error_total.labels(error_type="decode_error").inc()
                raise ValueError("Invalid encrypted token format")
            
            if len(raw) < 12:
                crypto_decrypt_error_total.labels(error_type="invalid_length").inc()
                raise ValueError("Encrypted blob too short - missing nonce")
            
            # Split nonce and ciphertext
            nonce = raw[:12]
            ciphertext = raw[12:]
            
            # Decrypt and verify authentication tag
            try:
                result = self.aes.decrypt(nonce, ciphertext, None)
                crypto_decrypt_total.inc()
                return result
            except InvalidTag as e:
                logger.error(f"Decryption failed - authentication tag invalid (tampering detected): {e}")
                crypto_decrypt_error_total.labels(error_type="invalid_tag").inc()
                raise ValueError("Failed to decrypt token - authentication failed")
            except Exception as e:
                logger.error(f"Decryption failed - token may be corrupted: {e}")
                crypto_decrypt_error_total.labels(error_type="decrypt_error").inc()
                raise ValueError("Failed to decrypt token")


# Global singleton instance
crypto = Crypto()
