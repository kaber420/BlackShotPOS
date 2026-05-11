# Plan: Sistema de Reservas Reactivo (V2)

Este plan describe la implementación de un sistema de reservas de mesas de alto rendimiento, evitando el uso de polling ineficiente y priorizando la consistencia de datos mediante estados calculados y programación de eventos en memoria.

## 1. Arquitectura Técnica

### A. Estado Virtual y Dinámico
En lugar de almacenar el estado "Reservada" de forma persistente en la tabla `Table`, el estado se determinará dinámicamente:
- Al consultar las mesas (`GET /tables`), el backend cruzará los datos con las reservas activas en la ventana de tiempo actual.
- Esto elimina la necesidad de tareas de sincronización constante en la base de datos.

### B. Programación de Eventos (Event-Driven)
- **Scheduler en Memoria**: Al crear o actualizar una reserva, el sistema calculará el `delay` hasta la hora de activación (ej. 30 min antes de la reserva).
- **Disparador**: Se utilizará `asyncio.get_event_loop().call_later()` o un scheduler ligero para emitir un evento de WebSocket (`tables.status_changed`) exactamente cuando la mesa deba pasar a estado visual de "Reservada".

## 2. Cambios Propuestos

### Backend (pos_core)

#### [NEW] [Reservation Model](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/pos_core/tables/models.py)
```python
class Reservation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    table_id: int = Field(foreign_key="table.id")
    customer_id: Optional[UUID] = Field(default=None, foreign_key="customer.id")
    customer_name: str
    customer_phone: Optional[str] = None
    reservation_at: datetime
    end_at: Optional[datetime] = None  # Duración estimada
    people_count: int = Field(default=2)
    status: str = Field(default="Confirmed") # Confirmed, Cancelled, Completed, No-show
    notes: Optional[str] = None
```

#### [NEW] [Reservation Service](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/pos_core/tables/reservation_service.py)
- Lógica de negocio para validación de colisiones (no permitir dos reservas que se solapen en la misma mesa).
- Integración con el `pos_core.events.bus` para disparar eventos `reservations.created`.
- **Manager de Timers**: Clase encargada de mantener los temporizadores en memoria para notificar cambios de estado visual.

#### [MODIFY] [Table Service](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/pos_core/tables/service.py)
- Refactorizar `get_tables` para inyectar el "Effective Status" basado en las reservas del momento.

### Frontend (bs_frontend)

#### [NEW] [Reservation Dashboard](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/bs_frontend/src/lib/components/ReservationSidebar.svelte)
- Una vista lateral o panel que muestra el listado de reservas del día con filtros rápidos.

#### [MODIFY] [Table Card View](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/bs_frontend/src/routes/(app)/tables/+page.svelte)
- Mostrar un indicador de "Próxima Reserva" en mesas que tienen un evento programado pronto.
- Acción de "Check-in": Si una mesa está reservada, el botón de "Ocupar" cargará automáticamente los datos del cliente de la reserva en la nueva orden.

## 3. Ventajas de este Enfoque
1. **Eficiencia**: Zero polling. La base de datos solo se toca cuando hay cambios reales.
2. **Consistencia**: Al ser un estado calculado, no hay riesgo de que una mesa se quede "trabada" en estado Reservada si el servidor se reinicia o falla una tarea.
3. **Escalabilidad**: El manejo de timers en memoria es extremadamente ligero comparado con consultas recurrentes.

## 4. Plan de Verificación
- Simulación de múltiples reservas concurrentes para validar el algoritmo de colisiones.
- Verificación de la propagación instantánea del estado "Reservada" vía WebSockets al llegar al umbral de tiempo configurado.
