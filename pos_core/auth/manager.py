import os
from typing import Optional
from uuid import UUID
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, UUIDIDMixin
from pos_core.auth.models import User
from pos_core.auth.db import get_user_db

SECRET = os.getenv("OMNIVAULT_SEED", "SECRET_DE_DESARROLLO_CAMBIAME")

class UserManager(UUIDIDMixin, BaseUserManager[User, UUID]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        print(f"User {user.id} has registered.")
        from pos_core.events.bus import event_bus
        await event_bus.publish("auth.user_registered", {"user_id": str(user.id), "email": user.email})

    async def on_after_login(
        self, user: User, response: Optional[Request] = None, request: Optional[Request] = None
    ):
        from pos_core.events.bus import event_bus
        await event_bus.publish("auth.user_login", {"user_id": str(user.id), "email": user.email})

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"User {user.id} forgot their password. Reset token: {token}")

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"Verification requested for user {user.id}. Verification token: {token}")

async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)
