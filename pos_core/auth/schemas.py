from uuid import UUID
from typing import Optional
from pydantic import EmailStr
from fastapi_users import schemas

class UserRead(schemas.BaseUser[UUID]):
    username: str
    organization_id: str
    is_remote: bool
    external_id: Optional[str] = None
    custom_metadata: dict = {}

class UserCreate(schemas.BaseUserCreate):
    username: str
    organization_id: str = "default"
    is_remote: bool = False
    external_id: Optional[str] = None
    custom_metadata: dict = {}

class UserUpdate(schemas.BaseUserUpdate):
    username: Optional[str] = None
    organization_id: Optional[str] = None
    is_remote: Optional[bool] = None
    external_id: Optional[str] = None
    custom_metadata: Optional[dict] = None

