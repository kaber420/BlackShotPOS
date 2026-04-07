import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from typing import Optional

class OmniVault:
    """
    OmniVault provides identity-linked encryption (Self-Sovereign).
    Keys are derived from the user's UUID and a system-wide seed.
    In production, this would integrate with Certberus to use actual user certificates.
    """
    def __init__(self, master_key_seed: Optional[str] = None):
        # In a real scenario, this seed comes from an HSM or TPM via Certberus
        self.seed = master_key_seed or os.getenv("OMNIVAULT_SEED", "omnisuite-sovereign-identity-seed")

    def _derive_key(self, user_uuid: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        # The key is bound to the unique user UUID
        return kdf.derive(f"{self.seed}:{user_uuid}".encode())

    def encrypt(self, user_uuid: str, plaintext: str) -> str:
        """Encrypts data for a specific user."""
        salt = os.urandom(16)
        key = self._derive_key(user_uuid, salt)
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
        # Store as salt(16) + nonce(12) + ciphertext
        return base64.b64encode(salt + nonce + ciphertext).decode()

    def decrypt(self, user_uuid: str, encrypted_data: str) -> str:
        """Decrypts data for a specific user."""
        try:
            data = base64.b64decode(encrypted_data)
            salt = data[:16]
            nonce = data[16:28]
            ciphertext = data[28:]
            key = self._derive_key(user_uuid, salt)
            aesgcm = AESGCM(key)
            return aesgcm.decrypt(nonce, ciphertext, None).decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")

# Global vault instance
vault = OmniVault()
