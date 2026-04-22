# Refactorización Profesional - Fase 1: Guía de Implementación Exacta

Este documento contiene el código exacto y las instrucciones directas para implementar la **Fase 1 (Cimientos)** de la refactorización de Blackshot POS. No hay ambigüedades; este es el código que debe ir en cada archivo.

---

## 1. Manejo Global de Excepciones

Actualmente el sistema devuelve errores `500` cuando falla la lógica de negocio. Vamos a controlarlo lanzando excepciones HTTP estructuradas.

### A. Crear el archivo `pos_core/exceptions.py`
Copia y pega el siguiente código para definir nuestra clase base de error:

```python
from fastapi import HTTPException

class BusinessLogicError(HTTPException):
    """
    Excepción base para todos los errores de reglas de negocio controlados.
    Permite al frontend procesar los errores uniformemente.
    """
    def __init__(self, detail: str, error_code: str, status_code: int = 400):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code

class OrderNotFoundError(BusinessLogicError):
    def __init__(self, order_id: int):
        super().__init__(
            detail=f"No se encontró la orden con ID {order_id}",
            error_code="ORDER_NOT_FOUND",
            status_code=404
        )

class InvalidOrderStateError(BusinessLogicError):
    def __init__(self, message: str):
        super().__init__(
            detail=message,
            error_code="INVALID_ORDER_STATE",
            status_code=400
        )
```

### B. Registrar el Handler en FastAPI (`main.py` o donde declares la app)
Debes capturar esta excepción a nivel global para asegurar que siempre devuelva el formato correcto, no importa dónde se lance el error.

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from pos_core.exceptions import BusinessLogicError

# ... donde declaras app = FastAPI(...)

@app.exception_handler(BusinessLogicError)
async def business_logic_exception_handler(request: Request, exc: BusinessLogicError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "detail": exc.detail
        },
    )
```

---

## 2. Pydantic DTOs (Schemas) para Órdenes

El principal cuello de botella actual es `format_order_json` en `service.py`. Este mapeo manual causa bugs y es difícil de mantener. Lo reemplazaremos usando la característica `from_attributes=True` de Pydantic.

### A. Crear el archivo `pos_core/sales/schemas.py`
Copia y pega este código. Estos modelos de Pydantic servirán para "traducir" automáticamente los modelos de la Base de Datos (`SQLModel`) a un JSON seguro para el frontend.

```python
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from pos_core.sales.models import OrderType, OrderStatus, PaymentMethod

# --- SCHEMAS BÁSICOS ---

class ProductSimpleRead(BaseModel):
    id: int
    name: str
    
    model_config = ConfigDict(from_attributes=True)

class ModifierSimpleRead(BaseModel):
    id: int
    name: str
    price_adjustment: float
    
    model_config = ConfigDict(from_attributes=True)

# --- SCHEMAS DE ORDEN ---

class PaymentRead(BaseModel):
    id: int
    method: PaymentMethod
    amount: float
    timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)

class OrderItemRead(BaseModel):
    id: int
    product_id: int
    product_variant_id: Optional[int]
    quantity: int
    unit_price: float
    status: OrderStatus
    # Relaciones que SQLModel debe popular y Pydantic debe extraer:
    product: Optional[ProductSimpleRead] = None
    modifiers: List[ModifierSimpleRead] = []
    
    # Timestamps y Rastreo
    delivered_by_name: Optional[str] = None
    cook_name: Optional[str] = None
    preparing_at: Optional[datetime] = None
    ready_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class OrderRead(BaseModel):
    id: int
    type: OrderType
    status: OrderStatus
    is_paid: bool
    table_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    # Empleados involucrados
    waiter_name: Optional[str] = None
    cook_name: Optional[str] = None
    
    # Timestamps
    preparing_at: Optional[datetime] = None
    ready_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None

    # Relaciones anidadas (Pydantic extraerá automáticamente la lista de la BD)
    items: List[OrderItemRead] = []
    payments: List[PaymentRead] = []
    
    model_config = ConfigDict(from_attributes=True)
```

### B. Cómo usar los Schemas en los Servicios y Routers
El objetivo final de esta fase es que cualquier función que retorne órdenes use este modelo. 

**En `pos_core/sales/router.py` (Ejemplo):**
```python
# Importar el schema
from pos_core.sales.schemas import OrderRead

# ACTUALIZAR EL RESPONSE_MODEL
@router.get("/orders", response_model=List[OrderRead])
async def get_orders(session: AsyncSession = Depends(get_session)):
    # Ejecutar la consulta en BD (Idealmente movido al Repository en Fase 2)
    result = await session.exec(select(Order).options(selectinload(Order.items)))
    orders_db = result.unique().all()
    
    # Retornar el modelo de BD directamente. 
    # FastAPI usará 'OrderRead' para convertir SQLAlchemy a JSON automáticamente.
    return orders_db 
```

**En Websockets (`trigger_broadcast` o similar):**
```python
from pos_core.sales.schemas import OrderRead

async def emit_order_update(order_db_model):
    # Ya no se usa format_order_json()
    # Pydantic parsea el ORM a diccionario en 1 línea
    order_dict = OrderRead.model_validate(order_db_model).model_dump(mode="json")
    await broadcast_message("order_updated", order_dict)
```

---

*Al implementar este documento de forma literal, el sistema estará listo para la Fase 2 sin romper compatibilidad con el frontend de SvelteKit.*
