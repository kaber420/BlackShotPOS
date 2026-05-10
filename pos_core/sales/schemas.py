from typing import List, Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from pos_core.sales.models import OrderType, OrderStatus, PaymentMethod

# ---------------------------------------------------------------------------
# SCHEMAS DE INVENTARIO (espejo de inventory/models.py para órdenes)
# ---------------------------------------------------------------------------

class MeasureRead(BaseModel):
    id: int
    name: str
    value: float
    unit: str

    model_config = ConfigDict(from_attributes=True)

class VariantRead(BaseModel):
    id: int
    price: float
    measure: Optional[MeasureRead] = None

    model_config = ConfigDict(from_attributes=True)

class ProductSimpleRead(BaseModel):
    id: int
    name: str
    recipe_markdown: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ModifierSimpleRead(BaseModel):
    id: int
    name: str
    extra_price: float

    model_config = ConfigDict(from_attributes=True)

# ---------------------------------------------------------------------------
# SCHEMAS DE PAGO
# ---------------------------------------------------------------------------

class PaymentRead(BaseModel):
    id: int
    method: PaymentMethod
    amount: float
    tip_amount: float = 0.0
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

# ---------------------------------------------------------------------------
# SCHEMA DE ÍTEM DE ORDEN  (espejo 1:1 de format_order_json → items_data)
# ---------------------------------------------------------------------------

class OrderItemRead(BaseModel):
    id: int
    product_id: int
    product_variant_id: Optional[int] = None
    quantity: int
    unit_price: float
    tax_rate: float = 0.0
    tax_amount: float = 0.0
    status: OrderStatus

    # Relaciones anidadas
    product: Optional[ProductSimpleRead] = None
    variant: Optional[VariantRead] = None
    modifiers: List[ModifierSimpleRead] = []

    model_config = ConfigDict(from_attributes=True)

# ---------------------------------------------------------------------------
# SCHEMA DE ORDEN  (espejo 1:1 de format_order_json → dict raíz)
# ---------------------------------------------------------------------------

class OrderRead(BaseModel):
    id: int
    type: OrderType
    status: OrderStatus
    subtotal: float = 0.0
    tax_amount: float = 0.0
    total_amount: float = 0.0
    balance_due: float = 0.0
    table_id: Optional[int] = None
    shift_id: Optional[int] = None
    external_reference: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    customer_id: Optional[UUID] = None

    # Rastreo del mesero creador
    waiter_uuid: Optional[str] = None
    waiter_name: Optional[str] = None

    # Relaciones anidadas
    items: List[OrderItemRead] = []
    payments: List[PaymentRead] = []

    model_config = ConfigDict(from_attributes=True)

# ---------------------------------------------------------------------------
# SCHEMAS DE DIVISIÓN DE CUENTA
# ---------------------------------------------------------------------------

class SplitItemCreate(BaseModel):
    item_id: int
    quantity: int

class SplitOrderCreate(BaseModel):
    items: List[SplitItemCreate]
