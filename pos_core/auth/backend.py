import os
from fastapi_users.authentication import (
    AuthenticationBackend,
    CookieTransport,
    JWTStrategy,
)

SECRET = os.getenv("OMNIVAULT_SEED", "SECRET_DE_DESARROLLO_CAMBIAME")

cookie_transport = CookieTransport(
    cookie_name="bs_auth",
    cookie_max_age=3600 * 24,  # 24 horas
    cookie_httponly=True,
    cookie_samesite="lax",
    cookie_secure=False, # Importante para desarrollo local sin HTTPS
)

def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600 * 24)

auth_backend = AuthenticationBackend(
    name="jwt-cookie",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)
