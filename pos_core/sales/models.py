from typing import Optional, List
from enum import Enum
from datetime import datetime, timezone
from uuid import UUID
from sqlmodel import SQLModel, Field, Relationship
from pydantic import field_validator, field_serializer
from pos_core.catalog.models import Modifier, Product, ProductVariant

class OrderType(str, Enum):
    DINE_IN = "DINE_IN"
    TAKEAWAY = "TAKEAWAY"
    DELIVERY = "DELIVERY"

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    PREPARING = "PREPARING"
    PAID = "PAID"
    READY = "READY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

class PaymentMethod(str, Enum):
    CASH = "CASH"
    CARD = "CARD"
    TRANSFER = "TRANSFER"

class OrderFinancialStatus(str, Enum):
    UNPAID = "UNPAID"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    REFUNDED = "REFUNDED"
    COMPLIMENTARY = "COMPLIMENTARY"



class OrderItemModifier(SQLModel, table=True):
    """Vínculo entre un item de la orden y los modificadores seleccionados en el POS."""
    order_item_id: int = Field(foreign_key="orderitem.id", primary_key=True)
    modifier_id: int = Field(foreign_key="modifier.id", primary_key=True)

class OrderItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.id", index=True)
    product_id: int = Field(foreign_key="product.id")
    product_variant_id: Optional[int] = Field(default=None, foreign_key="productvariant.id")
    quantity: int = Field(default=1)
    unit_price: float = Field(description="Precio unitario al momento de la venta")
    tax_rate: float = Field(default=0.0, description="Tasa de impuesto aplicada (snapshot)")
    tax_amount: float = Field(default=0.0, description="Monto de impuesto para este ítem")
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
    order_id: int = Field(foreign_key="order.id", index=True)
    method: PaymentMethod
    amount: float
    received_amount: float = Field(default=0.0)
    change_amount: float = Field(default=0.0)
    tip_amount: float = Field(default=0.0, description="Monto de propina incluido en este pago")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(), index=True)
    
    @field_serializer("timestamp")
    def serialize_payment_time(self, v: Optional[datetime]) -> Optional[str]:
        if v is None: return None
        if v.tzinfo is None: v = v.replace(tzinfo=timezone.utc)
        return v.isoformat()
    
    order: "Order" = Relationship(back_populates="payments")

class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    type: OrderType
    status: OrderStatus = Field(default=OrderStatus.PENDING, index=True)
    financial_status: OrderFinancialStatus = Field(default=OrderFinancialStatus.UNPAID, index=True)
    courtesy_reason: Optional[str] = Field(default=None)
    courtesy_by_uuid: Optional[str] = Field(default=None)
    
    # Snapshot Financiero
    subtotal: float = Field(default=0.0)
    tax_amount: float = Field(default=0.0)
    total_amount: float = Field(default=0.0)
    
    table_id: Optional[int] = Field(default=None, foreign_key="table.id", index=True)
    shift_id: Optional[int] = Field(default=None, foreign_key="shift.id")
    customer_id: Optional[UUID] = Field(default=None, foreign_key="customer.id")
    external_reference: Optional[str] = Field(default=None, description="PIN de Uber, ID de Rappi, etc.")
    created_at: datetime = Field(default_factory=lambda: datetime.now(), index=True)
    updated_at: datetime = Field(default_factory=lambda: datetime.now())

    # ── Rastreo del mesero creador ────────────────────────────────────────────
    waiter_uuid: Optional[str] = Field(default=None, description="UUID del mesero que creó la orden")
    waiter_name: Optional[str] = Field(default=None, description="Nombre del mesero (snapshot de auditoría)")

    items: List[OrderItem] = Relationship(back_populates="order")
    payments: List[Payment] = Relationship(back_populates="order")
    # shift: Optional["Shift"] = Relationship(back_populates="orders")


    @property
    def total_price(self) -> float:
        """Alias para mantener compatibilidad con código existente que usa total_price."""
        return self.total_amount

    @property
    def balance_due(self) -> float:
        """Calcula el saldo pendiente de la orden."""
        paid_amount = sum(p.amount for p in self.payments)
        return max(0.0, self.total_amount - paid_amount)


