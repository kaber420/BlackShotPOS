from typing import Optional
from sqlmodel import SQLModel, Field

from datetime import datetime, timezone
from pydantic import field_validator, field_serializer

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
