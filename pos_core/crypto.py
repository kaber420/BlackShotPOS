import os
from cryptography.fernet import Fernet

# Intentamos obtener la llave de cifrado desde las variables de entorno
# En desarrollo, si no existe, generamos una por defecto para no romper el flujo
_MASTER_KEY = os.getenv("CUSTOMER_PII_ENCRYPTION_KEY")
if not _MASTER_KEY:
    # WARN: Esto es solo para evitar caídas en desarrollo.
    # En producción DEBE estar configurada en el .env
    _MASTER_KEY = Fernet.generate_key().decode()

_fernet = Fernet(_MASTER_KEY.encode())

import hashlib
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

class CryptoService:
    @staticmethod
    def encrypt_data(data: str) -> str:
        if not data:
            return data
        return _fernet.encrypt(data.encode()).decode()

    @staticmethod
    def decrypt_data(encrypted_data: str) -> str:
        if not encrypted_data:
            return encrypted_data
        try:
            return _fernet.decrypt(encrypted_data.encode()).decode()
        except Exception:
            # En caso de fallo (ej. llave incorrecta o datos no cifrados por error)
            return encrypted_data

    @staticmethod
    def hash_data(data: str) -> str:
        if not data:
            return data
        return hashlib.sha256(data.encode()).hexdigest()

    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)
