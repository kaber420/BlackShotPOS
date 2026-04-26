from fastapi import APIRouter
from fastapi_users import FastAPIUsers
from pos_core.auth.models import User
from pos_core.auth.schemas import UserRead, UserCreate, UserUpdate
from pos_core.auth.manager import get_user_manager
from pos_core.auth.backend import auth_backend
from uuid import UUID

fastapi_users = FastAPIUsers[User, UUID](
    get_user_manager,
    [auth_backend],
)

auth_router = APIRouter()

# Rutas de login/logout
auth_router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/jwt",
    tags=["Auth"],
)

# Rutas de registro
auth_router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/register",
    tags=["Auth"],
)

# Rutas de gestión de usuarios (/me, etc)
user_router = fastapi_users.get_users_router(UserRead, UserUpdate)
