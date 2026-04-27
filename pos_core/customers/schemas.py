from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr

class CustomerBase(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    custom_metadata: dict = {}

class CustomerCreate(CustomerBase):
    organization_id: str = "default"

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    points: Optional[int] = None
    custom_metadata: Optional[dict] = None
    is_synced: Optional[bool] = None

class CustomerRead(CustomerBase):
    id: UUID
    points: int
    organization_id: str
    is_synced: bool
    last_visit_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True
