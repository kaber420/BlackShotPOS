# Plan de Implementación: Sistema de Reservaciones

Este documento detalla la estrategia para implementar un módulo de gestión de reservaciones en el ecosistema Blackshot, integrándose con el mapa de mesas existente y permitiendo un flujo fluido desde la reserva hasta la creación de la orden.

## 1. Objetivos
*   Permitir el registro de reservaciones futuras con datos de contacto.
*   Visualizar reservaciones en un formato de calendario/lista.
*   Automatizar el cambio de estado de las mesas basado en el horario de reserva.
*   Facilitar el "Check-in" de clientes reservados para abrir su cuenta rápidamente.

## 2. Cambios en Modelos (Backend)

### [NEW] `pos_core/tables/models.py` (Adiciones)
Añadiremos el modelo `Reservation` y un Enum para sus estados.

```python
class ReservationStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"

class Reservation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_name: str = Field(index=True)
    customer_phone: Optional[str] = None
    customer_id: Optional[UUID] = Field(default=None, foreign_key="customer.id")
    
    table_id: Optional[int] = Field(default=None, foreign_key="table.id", index=True)
    pax: int = Field(default=2)
    
    reservation_time: datetime = Field(index=True)
    status: ReservationStatus = Field(default=ReservationStatus.PENDING)
    notes: Optional[str] = None
    
    # Auditoría y Sincronización
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    organization_id: str = Field(default="default", index=True)
    is_synced: bool = Field(default=False)
```

## 3. Lógica de Negocio (`pos_core/tables/service.py`)

Se implementarán las siguientes funciones:
*   `create_reservation`: Validar que la mesa no tenga conflictos de horario (ej: margen de 2 horas entre reservas).
*   `check_in_reservation`: 
    1.  Cambiar estado de la reserva a `COMPLETED`.
    2.  Asignar la mesa como `Occupied`.
    3.  Llamar al servicio de ventas para abrir una nueva `Order` vinculada a la mesa y al cliente.
*   `auto_update_table_status`: Un proceso (o disparador por tiempo) que marque las mesas como `Reserved` en el mapa cuando falten N minutos para la reservación.

## 4. API Endpoints (`pos_core/tables/router.py`)

*   `GET /tables/reservations`: Listar reservaciones por rango de fecha.
*   `POST /tables/reservations`: Crear nueva reserva.
*   `PATCH /tables/reservations/{id}/status`: Cambiar estado (Confirmar, Cancelar, No Show).
*   `POST /tables/reservations/{id}/check-in`: Ejecutar el flujo de llegada del cliente.

## 5. Frontend (`bs_frontend`)

### Componentes Sugeridos:
1.  **`ReservationManager.svelte`:** Nueva vista en el Control Center con un mini-calendario y lista de hoy/mañana.
2.  **`ReservationModal.svelte`:** Formulario para captura rápida (Nombre, Tel, Mesa, Hora).
3.  **Integración con `TableMap`:**
    *   Indicador visual (Badge o color) en la mesa si tiene una reserva próxima.
    *   Tool-tip al pasar el mouse con los datos de la reserva.

## 6. Sincronización (`bs_sync`)
Las reservaciones deberán sincronizarse con la Central para permitir:
*   Reservaciones en línea (vía API de la Central).
*   Visualización de agenda desde el Dashboard Administrativo centralizado.

---
## Próximos Pasos
1.  Crear migraciones/modelos en el backend.
2.  Implementar servicios CRUD de reservaciones.
3.  Desarrollar la interfaz de captura en el frontend.
