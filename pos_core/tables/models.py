from typing import Optional
from sqlmodel import SQLModel, Field

class Table(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    number: int = Field(unique=True, index=True)
    capacity: int = Field(default=4)
    status: str = Field(default="Free")  # Free, Occupied, Reserved, Out of order
    location: Optional[str] = None  # Terraza, Salón, Segundo piso, etc.
    
    is_active: bool = Field(default=True)
