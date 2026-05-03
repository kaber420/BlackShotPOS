# Cash Management Backend - Technical Specification

Este documento detalla la implementación del sistema de cajas y cortes para el ecosistema Blackshot.

## 1. Modelos de Base de Datos (SQLModel)

### CashRegister (Caja Física/Lógica)
Representa el punto de venta físico o lógico.
```python
class CashRegister(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True) # Ej: "Barra 1", "Caja Principal"
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

### CashMovement (Entradas/Salidas)
Para registrar retiros de efectivo o ingresos manuales.
```python
class CashMovementType(str, Enum):
    INCOME = "INCOME"   # Fondo extra, corrección
    EXPENSE = "EXPENSE" # Pago a proveedor, retiro parcial

class CashMovement(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    shift_id: int = Field(foreign_key="shift.id")
    amount: float
    type: CashMovementType
    reason: str
    user_id: UUID = Field(foreign_key="user.id")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

### Shift (Turno/Corte) - MODIFICACIONES
Actualizaremos el modelo actual para soportar múltiples métodos y la relación con la caja.
```python
class Shift(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    register_id: int = Field(foreign_key="cashregister.id")
    user_id: UUID = Field(foreign_key="user.id")
    
    start_time: datetime
    end_time: Optional[datetime]
    status: str # OPEN, CLOSED
    
    # --- Financiero ---
    initial_cash: float
    
    # Totales esperados (calculados por el sistema)
    expected_cash: float     # initial + ventas_cash + movimientos_in - movimientos_out
    expected_card: float     # ventas_card
    expected_transfer: float # ventas_transfer
    
    # Totales reales (ingresados por el usuario al cerrar)
    actual_cash: Optional[float]
    actual_card: Optional[float]
    actual_transfer: Optional[float]
    
    # Diferencias
    difference_cash: Optional[float]
    notes: Optional[str]
```

## 2. Lógica de Negocio (AccountingService)

### `calculate_totals(shift_id)`
Calcula el estado actual de la caja sumando:
1.  **Ventas por Método**: `select sum(amount) from Payment where order.shift_id = X group by method`.
2.  **Movimientos**: `select sum(amount) from CashMovement where shift_id = X group by type`.
3.  **Resultado**: `initial_cash + cash_sales + movements_in - movements_out`.

### `generate_z_cut(shift_id)`
1.  Calcula los totales esperados.
2.  Compara con los totales reales ingresados.
3.  Marca el turno como `CLOSED`.
4.  Genera un snapshot para auditoría.

## 3. Endpoints de API

*   `GET /registers/`: Lista cajas disponibles y su estado (abierta/cerrada).
*   `POST /shifts/open`: Abre un turno. Requiere `register_id` e `initial_cash`.
*   `POST /shifts/{id}/movement`: Registra una entrada o salida de efectivo.
*   `GET /shifts/{id}/x-cut`: Devuelve el estado actual sin cerrar.
*   `POST /shifts/{id}/close`: Cierre definitivo (Z-Cut).
