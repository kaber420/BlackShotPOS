from typing import Optional, List
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID
from sqlmodel import SQLModel, Field, Relationship
from pydantic import field_serializer

class CashRegister(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True) # Ej: "Barra 1", "Caja Principal"
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class CashMovementType(str, Enum):
    INCOME = "INCOME"         # Fondo extra, corrección
    EXPENSE = "EXPENSE"       # Pago a proveedor, gasto operativo
    WITHDRAWAL = "WITHDRAWAL" # Retiro parcial de seguridad (Corte Parcial)

class CashMovementCategory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    type: CashMovementType
    description: Optional[str] = None

class CashMovement(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    shift_id: int = Field(foreign_key="shift.id")
    category_id: Optional[int] = Field(default=None, foreign_key="cashmovementcategory.id")
    amount: float
    type: CashMovementType
    reason: str
    user_id: UUID = Field(foreign_key="user.id")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    shift: Optional["Shift"] = Relationship(back_populates="movements")

class ShiftStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"

class Shift(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    register_id: Optional[int] = Field(default=None, foreign_key="cashregister.id")
    user_id: Optional[UUID] = Field(default=None, foreign_key="user.id")
    
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    end_time: Optional[datetime] = Field(default=None)
    status: ShiftStatus = Field(default=ShiftStatus.OPEN)
    
    # --- Financiero ---
    initial_cash: float
    
    # Totales esperados (calculados por el sistema)
    expected_cash: float = Field(default=0.0)
    expected_card: float = Field(default=0.0)
    expected_transfer: float = Field(default=0.0)
    
    # Totales reales (ingresados por el usuario al cerrar)
    actual_cash: Optional[float] = Field(default=None)
    actual_card: Optional[float] = Field(default=None)
    actual_transfer: Optional[float] = Field(default=None)
    
    # Diferencias
    difference_cash: Optional[float] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    
    @field_serializer("start_time", "end_time")
    def serialize_shift_times(self, v: Optional[datetime]) -> Optional[str]:
        if v is None: return None
        if v.tzinfo is None: v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()
    
    movements: List["CashMovement"] = Relationship(back_populates="shift", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

