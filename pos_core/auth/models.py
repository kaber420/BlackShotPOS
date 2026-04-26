from uuid import UUID, uuid4
from typing import Optional
from sqlmodel import SQLModel, Field, Column, JSON
from pydantic import ConfigDict

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
