# Plan de Implementación: Historial de Consumos, Visitas y Preferencias en el Portal de Clientes

Este documento define la arquitectura técnica y el plan de implementación para dotar al Portal de Clientes con transparencia total sobre sus consumos. El cliente podrá auditar sus compras anteriores, ver en qué gastó su monedero/crédito, y visualizar estadísticas interactivas sobre su comportamiento de consumo (bebida favorita, visitas totales y última sucursal visitada).

---

## 1. Diseño de la Solución Backend (FastAPI)

Dado que BlackShot opera con un esquema **offline-first** por sucursal, el historial de compras local en el POS representa fielmente sus consumos en la sucursal actual. 

### A. Nuevos Modelos de Respuesta (Schemas)
En `pos_core/customers/schemas.py`, definiremos las estructuras de datos que se enviarán al portal de clientes de forma segura y optimizada:

```python
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID

class CustomerOrderItemRead(BaseModel):
    product_name: str
    quantity: int
    unit_price: float
    measure_name: Optional[str] = None

class CustomerOrderRead(BaseModel):
    id: int
    created_at: datetime
    branch_name: str
    total_amount: float
    financial_status: str
    items: List[CustomerOrderItemRead]
    payment_methods: List[str]

class CustomerStatsRead(BaseModel):
    total_visits: int
    total_spent: float
    favorite_product: Optional[str] = None
    favorite_branch: str
    last_visit_at: Optional[datetime] = None
```

### B. Nuevos Endpoints en el Router Público (`pos_core/customers/public_router.py`)
Implementaremos dos rutas públicas seguras que consumen el token JWT del cliente:

1. **`GET /api/v1/public/customers/me/orders`**:
   - Obtiene todas las órdenes del cliente actual (`current_customer.id`) ordenadas por fecha descendente.
   - Resuelve el nombre del producto, cantidad, precio e incluye el nombre de la sucursal leyendo `BusinessSettings` de la base de datos local.
   
2. **`GET /api/v1/public/customers/me/stats`**:
   - Calcula el total de visitas (cantidad de órdenes pagadas).
   - Suma el gasto total acumulado.
   - Determina el producto más consumido (contando frecuencias en `OrderItem` agrupados por producto).
   - Extrae el nombre de la sucursal local activa desde `BusinessSettings`.

---

## 2. Diseño de la Solución Frontend (SvelteKit)

### A. Diseño de Interfaz en `/perfil` (Mi Perfil)
Añadiremos dos componentes visuales de alto impacto premium dentro de la vista `bs_customer_portal/src/routes/perfil/+page.svelte`:

1. **Panel de Estadísticas (Consumo y Fidelización)**:
   - Tres tarjetas en la parte superior con iconos modernos y fondos sutiles:
     - **Visitas Totales**: Con un contador dinámico.
     - **Mi Sucursal**: Indica cuál es sucursal favorita/última visitada.
     - **Bebida Favorita**: Muestra el nombre del producto estrella del cliente.

2. **Historial de Compras (Timeline Interactivo)**:
   - Una sección tipo *feed* o lista cronológica con todas las compras realizadas.
   - Desglose de cada compra mostrando:
     - Fecha formateada amigablemente (ej. *"Hoy, 15:30"* o *"14 May, 2026"*).
     - Detalle de ítems (ej. *"1x Capuccino Mediano, 1x Croissant"*).
     - Total pagado y métodos de pago representados con insignias (ej. *"Monedero"*, *"Tarjeta"*).

---

## 3. Cambios Propuestos en Archivos

### [MODIFY] [public_router.py](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/pos_core/customers/public_router.py)
- Incorporar las nuevas rutas `/me/orders` y `/me/stats`.
- Implementar la lógica para obtener la sucursal desde `BusinessSettings` y agregar la relación de `Order` e `OrderItem` mediante consultas eficientes en SQLAlchemy/SQLModel.

### [MODIFY] [schemas.py](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/pos_core/customers/schemas.py)
- Agregar las clases Pydantic para el formateo seguro del historial y las estadísticas.

### [MODIFY] [+page.svelte (perfil)](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/bs_customer_portal/src/routes/perfil/+page.svelte)
- Integrar la llamada a las APIs de `/me/orders` y `/me/stats` en la función `loadProfile`.
- Maquetar el componente visual de estadísticas y el timeline de compras con transiciones suaves (`fly`, `fade`, `slide`) y micro-animaciones en hover.

---

## 4. Plan de Verificación

### Pruebas Unitarias/API
1. Haremos una petición REST autenticada mediante `curl` o script local al nuevo endpoint `/api/v1/public/customers/me/orders` para verificar el JSON devuelto.
2. Confirmaremos que los datos de cálculo en `/api/v1/public/customers/me/stats` coincidan aritméticamente con los registros del sembrado.

### Pruebas de Interfaz (Frontend)
1. Navegaremos a `http://localhost:5174/perfil` en el navegador.
2. Verificaremos que el dashboard de estadísticas cargue fluidamente y que el historial despliegue el listado de compras con formato premium.
