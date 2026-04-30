from typing import Optional
from datetime import datetime, timezone
from enum import Enum
from sqlmodel import SQLModel, Field
from pydantic import field_serializer

class AuditCategory(str, Enum):
    SECURITY = "security"
    SALES = "sales"
    INVENTORY = "inventory"
    CONFIG = "config"

class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    category: AuditCategory
    action: str
    reason: Optional[str] = Field(default=None)
    actor_uuid: str
    actor_name: str
    target_id: Optional[str] = Field(default=None)
    target_type: Optional[str] = Field(default=None)
    changes_json: Optional[str] = Field(default=None)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_serializer("timestamp")
    def serialize_audit_time(self, v: Optional[datetime]) -> Optional[str]:
        if v is None: return None
        if v.tzinfo is None: v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()
