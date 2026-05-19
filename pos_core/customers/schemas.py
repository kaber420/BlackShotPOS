from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr

class CustomerBase(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    telegram_id: Optional[str] = None
    nfc_tag_id: Optional[str] = None
    loyalty_code: Optional[str] = None
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
    nfc_tag_id: Optional[str] = None
    loyalty_code: Optional[str] = None
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
    nfc_tag_id: Optional[str] = None
    loyalty_code: Optional[str] = None

    class Config:
        from_attributes = True

class CustomerOrderItemRead(BaseModel):
    product_name: str
    quantity: int
    unit_price: float
    measure_name: Optional[str] = None

class CustomerOrderRead(BaseModel):
    id: int
    created_at: datetime
    branch_name: str
    total_amount: float
    financial_status: str
    items: List[CustomerOrderItemRead]
    payment_methods: List[str]

class CustomerStatsRead(BaseModel):
    total_visits: int
    total_spent: float
    favorite_product: Optional[str] = None
    favorite_branch: str
    last_visit_at: Optional[datetime] = None

