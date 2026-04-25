from typing import Optional, List
from enum import Enum
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship
from pydantic import field_validator, field_serializer
from pos_core.inventory.models import Modifier, Product, ProductVariant

class OrderType(str, Enum):
    DINE_IN = "DINE_IN"
    TAKEAWAY = "TAKEAWAY"
    DELIVERY = "DELIVERY"

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    PREPARING = "PREPARING"
    READY = "READY"
    PAID = "PAID"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

class PaymentMethod(str, Enum):
    CASH = "CASH"
    CARD = "CARD"
    TRANSFER = "TRANSFER"

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

class OrderItemModifier(SQLModel, table=True):
    """Vínculo entre un item de la orden y los modificadores seleccionados en el POS."""
    order_item_id: int = Field(foreign_key="orderitem.id", primary_key=True)
    modifier_id: int = Field(foreign_key="modifier.id", primary_key=True)

class OrderItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.id")
    product_id: int = Field(foreign_key="product.id")
    product_variant_id: Optional[int] = Field(default=None, foreign_key="productvariant.id")
    quantity: int = Field(default=1)
    unit_price: float = Field(description="Precio unitario al momento de la venta")
    status: OrderStatus = Field(default=OrderStatus.PENDING)

    # ── Rastreo de entrega (¿quién entregó este ítem al cliente?) ────────────
    delivered_by_uuid: Optional[str] = Field(default=None)
    delivered_by_name: Optional[str] = Field(default=None)

    # ── Rastreo de cocina (¿qué cocinero preparó este ítem?) ────────────────
    cook_uuid: Optional[str] = Field(default=None)
    cook_name: Optional[str] = Field(default=None)

    # ── Timestamps de ciclo de vida por ítem ─────────────────────────────────
    preparing_at: Optional[datetime] = Field(default=None)
    ready_at: Optional[datetime] = Field(default=None)
    delivered_at: Optional[datetime] = Field(default=None)

    @field_serializer("preparing_at", "ready_at", "delivered_at")
    def serialize_item_times(self, v: Optional[datetime]) -> Optional[str]:
        if v is None: return None
        if v.tzinfo is None: v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()

    order: "Order" = Relationship(back_populates="items")
    product: "Product" = Relationship()
    variant: Optional["ProductVariant"] = Relationship()
    # Modificadores seleccionados para este item
    modifiers: List["Modifier"] = Relationship(link_model=OrderItemModifier)

    @property
    def subtotal(self) -> float:
        return self.quantity * self.unit_price

class Payment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.id")
    method: PaymentMethod
    amount: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @field_serializer("timestamp")
    def serialize_payment_time(self, v: Optional[datetime]) -> Optional[str]:
        if v is None: return None
        if v.tzinfo is None: v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()
    
    order: "Order" = Relationship(back_populates="payments")

class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    type: OrderType
    status: OrderStatus = Field(default=OrderStatus.PENDING)
    is_paid: bool = Field(default=False)
    table_id: Optional[int] = Field(default=None, foreign_key="table.id")
    shift_id: Optional[int] = Field(default=None, foreign_key="shift.id")
    external_reference: Optional[str] = Field(default=None, description="PIN de Uber, ID de Rappi, etc.")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # ── Rastreo del mesero creador ────────────────────────────────────────────
    waiter_uuid: Optional[str] = Field(default=None, description="UUID del mesero que creó la orden")
    waiter_name: Optional[str] = Field(default=None, description="Nombre del mesero (snapshot de auditoría)")

    # ── Rastreo del cocinero responsable ─────────────────────────────────────
    cook_uuid: Optional[str] = Field(default=None, description="UUID del cocinero que tomó/preparó la orden")
    cook_name: Optional[str] = Field(default=None, description="Nombre del cocinero (snapshot de auditoría)")

    # ── Timestamps de ciclo de vida de la orden ───────────────────────────────
    preparing_at: Optional[datetime] = Field(default=None, description="Cuando cocina empezó a preparar")
    ready_at: Optional[datetime] = Field(default=None, description="Cuando cocina marcó la orden como lista")
    delivered_at: Optional[datetime] = Field(default=None, description="Cuando el mesero entregó al cliente")

    @field_serializer("created_at", "updated_at", "preparing_at", "ready_at", "delivered_at")
    def serialize_order_times(self, v: Optional[datetime]) -> Optional[str]:
        if v is None: return None
        if v.tzinfo is None: v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()

    items: List[OrderItem] = Relationship(back_populates="order")
    payments: List[Payment] = Relationship(back_populates="order")
    shift: Optional[Shift] = Relationship(back_populates="orders")

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
