from uuid import UUID, uuid4
from typing import Optional
from sqlmodel import SQLModel, Field, Column, JSON
from pydantic import ConfigDict
from dataclasses import dataclass, field

@dataclass
class BridgeUser:
    """Usuario simulado para peticiones que vienen desde el Bridge (Central Management)"""
    id: UUID = field(default_factory=uuid4)
    email: str = "central@blackshot.app"
    is_active: bool = True
    is_superuser: bool = True
    is_verified: bool = True
    organization_id: str = "central"
    is_remote: bool = True
    external_id: str = "central-admin"
    custom_metadata: dict = field(default_factory=lambda: {"role": "admin", "is_bridge": True})

class User(SQLModel, table=True):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    # --- CAMPOS FastAPI Users ---
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(unique=True, index=True, nullable=False)
    hashed_password: str = Field(nullable=False)
    is_active: bool = Field(default=True, nullable=False)
    is_superuser: bool = Field(default=False, nullable=False)
    is_verified: bool = Field(default=False, nullable=False)
    
    # --- CAMPOS BRIDGE (DISTRIBUIDO) ---
    organization_id: str = Field(default="default", index=True, description="ID de la sucursal/organización")
    is_remote: bool = Field(default=False, description="¿Es un usuario de gestión regional/remota?")
    external_id: Optional[str] = Field(default=None, description="ID del usuario en el Panel Central")
    custom_metadata: dict = Field(default_factory=dict, sa_column=Column("metadata", JSON))
