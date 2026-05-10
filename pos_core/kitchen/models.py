from typing import Optional, List
from datetime import datetime, timezone
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship
from pydantic import field_serializer

class KitchenStatus(str, Enum):
    PENDING = "PENDING"
    PREPARING = "PREPARING"
    READY = "READY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

class ProductionAreaBase(SQLModel):
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    printer_ip: Optional[str] = None
    printer_port: int = Field(default=9100)
    printer_type: str = Field(default="network", description="network, bluetooth, usb")
    is_active: bool = Field(default=True)

class ProductionArea(ProductionAreaBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

class KitchenTicket(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(index=True)
    item_id: int = Field(index=True)
    
    # Snapshot de datos de la orden para independencia total del KDS
    table_id: Optional[int] = Field(default=None, index=True)
    order_type: str = Field(default="DINE_IN") # DINE_IN, TAKEAWAY, DELIVERY
    waiter_name: Optional[str] = None
    external_reference: Optional[str] = None

    # Snapshot de datos del producto
    product_name: str
    variant_name: Optional[str] = None
    modifiers_text: Optional[str] = None # Ej: "+ Sin cebolla, + Extra queso"
    
    production_area_id: Optional[int] = Field(default=None, foreign_key="productionarea.id")
    
    status: KitchenStatus = Field(default=KitchenStatus.PENDING, index=True)
    
    cook_uuid: Optional[str] = None
    cook_name: Optional[str] = None
    
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None

    @field_serializer("received_at", "started_at", "finished_at", "delivered_at")
    def serialize_times(self, v: Optional[datetime]) -> Optional[str]:
        if v is None: return None
        if v.tzinfo is None: v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()

    production_area: Optional[ProductionArea] = Relationship()

# Modelos de creación/lectura
class ProductionAreaCreate(ProductionAreaBase):
    pass

class ProductionAreaUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    printer_ip: Optional[str] = None
    printer_port: Optional[int] = None
    printer_type: Optional[str] = None
    is_active: Optional[bool] = None

class ProductionAreaRead(ProductionAreaBase):
    id: int

class KitchenTicketRead(SQLModel):
    id: int
    order_id: int
    item_id: int
    # Snapshot info
    table_id: Optional[int]
    order_type: str
    waiter_name: Optional[str]
    external_reference: Optional[str]
    
    product_name: str
    variant_name: Optional[str]
    modifiers_text: Optional[str]
    status: KitchenStatus
    received_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    production_area: Optional[ProductionAreaRead]
