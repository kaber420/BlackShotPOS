from typing import Optional, List
from enum import Enum
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
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
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = Field(default=None)
    initial_cash: float
    expected_cash: float = Field(default=0.0)
    actual_cash: Optional[float] = Field(default=None)
    difference: Optional[float] = Field(default=None)
    status: ShiftStatus = Field(default=ShiftStatus.OPEN)
    
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
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    order: "Order" = Relationship(back_populates="payments")

class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    type: OrderType
    status: OrderStatus = Field(default=OrderStatus.PENDING)
    is_paid: bool = Field(default=False)
    table_id: Optional[int] = Field(default=None, foreign_key="table.id")
    shift_id: Optional[int] = Field(default=None, foreign_key="shift.id")
    external_reference: Optional[str] = Field(default=None, description="PIN de Uber, ID de Rappi, etc.")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    items: List[OrderItem] = Relationship(back_populates="order")
    payments: List[Payment] = Relationship(back_populates="order")
    shift: Optional[Shift] = Relationship(back_populates="orders")

class AuditAction(str, Enum):
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ITEM_CANCELLED = "ITEM_CANCELLED"

class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    action: AuditAction
    reason: str
    actor_uuid: str
    actor_name: str
    order_id: Optional[int] = Field(default=None, foreign_key="order.id")
    order_item_id: Optional[int] = Field(default=None, foreign_key="orderitem.id")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
