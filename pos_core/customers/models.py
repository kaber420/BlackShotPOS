from typing import Optional
from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import JSON, Column

class Customer(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    phone: Optional[str] = Field(default=None, index=True, unique=True)
    name: str = Field(index=True)
    email: Optional[str] = Field(default=None, index=True)
    points: int = Field(default=0)
    
    # Infraestructura Distribuida
    organization_id: str = Field(default="default", index=True)
    is_synced: bool = Field(default=False, index=True)
    last_visit_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Metadata adicional (ej: preferencias, notas)
    custom_metadata: dict = Field(default={}, sa_type=JSON)

    # Relaciones
    # orders: List["Order"] = Relationship(back_populates="customer")
