from sqlmodel import SQLModel, Field
from typing import Optional, Any
from datetime import datetime
import uuid
from enum import Enum

class SyncStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SYNCED = "synced"
    FAILED = "failed"

class SyncEvent(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    topic: str = Field(index=True)
    payload: str  # JSON stringified
    status: SyncStatus = Field(default=SyncStatus.PENDING, index=True)
    attempts: int = Field(default=0)
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    synced_at: Optional[datetime] = None

    class Config:
        arbitrary_types_allowed = True
