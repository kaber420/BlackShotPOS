from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timezone
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship
from pydantic import field_serializer

if TYPE_CHECKING:
    from pos_core.sales.models import Order

class ShiftStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"

class Shift(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = Field(default=None)
    initial_cash: float
    expected_cash: float = Field(default=0.0)
    actual_cash: Optional[float] = Field(default=None)
    difference: Optional[float] = Field(default=None)
    status: ShiftStatus = Field(default=ShiftStatus.OPEN)
    
    @field_serializer("start_time", "end_time")
    def serialize_shift_times(self, v: Optional[datetime]) -> Optional[str]:
        if v is None: return None
        if v.tzinfo is None: v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()
    
    orders: List["Order"] = Relationship(back_populates="shift")
