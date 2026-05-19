from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr

class CustomerBase(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    telegram_id: Optional[str] = None
    custom_metadata: dict = {}
    accepts_marketing_email: bool = False
    accepts_marketing_telegram: bool = False

class CustomerCreate(CustomerBase):
    organization_id: str = "default"
    password: Optional[str] = None

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    telegram_id: Optional[str] = None
    points: Optional[int] = None
    credit_balance: Optional[float] = None
    tier: Optional[str] = None
    accepts_marketing_email: Optional[bool] = None
    accepts_marketing_telegram: Optional[bool] = None
    custom_metadata: Optional[dict] = None
    is_synced: Optional[bool] = None
    password: Optional[str] = None

class CustomerRead(CustomerBase):
    id: UUID
    points: int
    credit_balance: float
    tier: str
    total_spent: float
    total_visits: int
    organization_id: str
    is_synced: bool
    last_visit_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True
