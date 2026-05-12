from typing import Optional
from sqlmodel import SQLModel, Field
from enum import Enum
from datetime import datetime, timezone
from pydantic import field_validator, field_serializer
from uuid import UUID

class Table(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    number: int = Field(unique=True, index=True)
    capacity: int = Field(default=4)
    status: str = Field(default="Free")  # Free, Occupied, Reserved, Out of order
    location: Optional[str] = None  # Terraza, Salón, Segundo piso, etc.
    
    occupied_at: Optional[datetime] = Field(default=None)
    is_active: bool = Field(default=True)

    @field_serializer("occupied_at")
    def serialize_occupied_at(self, v: Optional[datetime]) -> Optional[str]:
        if v is None:
            return None
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()

class ReservationStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"

class Reservation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_name: str = Field(index=True)
    customer_phone: Optional[str] = None
    customer_id: Optional[UUID] = Field(default=None, foreign_key="customer.id")
    
    table_id: Optional[int] = Field(default=None, foreign_key="table.id", index=True)
    pax: int = Field(default=2)
    
    reservation_time: datetime = Field(index=True)
    status: ReservationStatus = Field(default=ReservationStatus.PENDING)
    notes: Optional[str] = None
    
    # Auditoría y Sincronización
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    organization_id: str = Field(default="default", index=True)
    is_synced: bool = Field(default=False)

    @field_serializer("reservation_time")
    def serialize_reservation_time(self, v: Optional[datetime]) -> Optional[str]:
        if v is None: return None
        if v.tzinfo is None: v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()

    @field_serializer("created_at")
    def serialize_created_at(self, v: Optional[datetime]) -> Optional[str]:
        if v is None: return None
        if v.tzinfo is None: v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()
