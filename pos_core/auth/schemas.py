from uuid import UUID
from typing import Optional
from pydantic import BaseModel, EmailStr

class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    is_active: bool
    is_superuser: bool
    is_verified: bool
    organization_id: str
    is_remote: bool
    external_id: Optional[str] = None
    custom_metadata: dict = {}

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    organization_id: str = "default"
    is_remote: bool = False
    external_id: Optional[str] = None
    custom_metadata: dict = {}

class UserUpdate(BaseModel):
    password: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    is_verified: Optional[bool] = None
    organization_id: Optional[str] = None
    is_remote: Optional[bool] = None
    external_id: Optional[str] = None
    custom_metadata: Optional[dict] = None
