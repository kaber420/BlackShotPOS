from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from uuid import UUID

if TYPE_CHECKING:
    from pos_core.auth.models import User
    from pos_core.catalog.models import ProductionArea, ProductionAreaRead

class IntercomMessageAreaLink(SQLModel, table=True):
    message_id: Optional[int] = Field(default=None, foreign_key="intercommessage.id", primary_key=True)
    area_id: Optional[int] = Field(default=None, foreign_key="productionarea.id", primary_key=True)

class IntercomMessageBase(SQLModel):
    sender_id: Optional[UUID] = Field(default=None, foreign_key="user.id")
    audio_path: str
    is_global: bool = Field(default=False)
    timestamp: datetime = Field(default_factory=datetime.now)

class IntercomMessage(IntercomMessageBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Relaciones
    sender: Optional["User"] = Relationship()
    target_areas: List["ProductionArea"] = Relationship(link_model=IntercomMessageAreaLink)

# --- Schemas para API ---

class IntercomMessageRead(SQLModel):
    id: int
    sender_id: Optional[UUID]
    sender_name: Optional[str] = None
    audio_url: str
    is_global: bool
    timestamp: datetime
    target_areas: List[int] = []
    area_names: List[str] = []

class IntercomMessageCreate(SQLModel):
    area_ids: Optional[List[int]] = None
    is_global: bool = False
