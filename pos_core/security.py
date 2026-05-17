from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response

# Configuración global del limitador de peticiones (Rate Limiting)
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

import nkeys
from nacl.signing import SigningKey

def generate_nkey_pair():
    """
    Genera un par de llaves Ed25519 compatible con la autenticación NKEY de NATS.
    Retorna una tupla: (seed_str, public_key_str)
    """
    signing_key = SigningKey.generate()
    raw_seed = signing_key.encode()
    encoded_seed = nkeys.encode_seed(raw_seed, prefix=nkeys.PREFIX_BYTE_USER)
    kp = nkeys.from_seed(encoded_seed)
    return encoded_seed.decode(), kp.public_key.decode()

