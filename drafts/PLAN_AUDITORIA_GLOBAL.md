# Plan: Sistema de Auditoría Global 360° - Blackshot POS

## 1. Visión General
El objetivo es transformar el log de auditoría actual (que solo registra cancelaciones) en un sistema centralizado que capture todos los eventos críticos del negocio. Esto permite detectar fraudes, errores operativos y cambios no autorizados en la configuración.

## 2. Categorías de Auditoría Propuestas

### A. Auditoría de Seguridad (Crítica)
*   **LOGIN_SUCCESS / LOGIN_FAILURE**: Rastreo de quién entra al sistema y bloqueos por intentos fallidos.
*   **PERMISSION_DENIED**: Registrar cada vez que un usuario intenta realizar una acción sin permiso (ej. un mesero tratando de ver reportes).
*   **USER_MANAGEMENT**: Registro de creación, edición (cambio de roles/permisos) y desactivación de empleados.
*   **ELEVATION_REQUESTED**: Cuando un manager autoriza una acción en la terminal de un mesero (vía PIN/Token).

### B. Auditoría de Precios y Menú
*   **PRICE_CHANGE**: Registrar el precio viejo vs el precio nuevo, quién lo cambió y cuándo.
*   **MENU_MODIFIED**: Creación o eliminación de productos y categorías.
*   **RECIPE_CHANGE**: Cambios en los ingredientes de una receta (vital para el costo de comida).

### C. Auditoría Operativa de Ventas
*   **DISCOUNT_APPLIED**: Registro de descuentos manuales aplicados a órdenes.
*   **DRAWER_OPENED**: Apertura manual del cajón de dinero (sin venta).
*   **REPRINT_TICKET**: Reimpresión de tickets de cuenta (posible indicador de fraude si es excesivo).
*   **ORDER_VOIDED**: Eliminación de ítems antes de pagar (ya implementado parcialmente).

### D. Auditoría de Inventario
*   **STOCK_ADJUSTMENT**: Correcciones manuales de inventario (merma, entrada de mercancía, pérdida).
*   **LOW_STOCK_ALERT**: Registro de cuándo un producto bajó del nivel crítico.

---

## 3. Estructura Técnica del Log
Expandiremos el modelo `AuditLog` para soportar metadatos enriquecidos:

```python
class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    category: str  # 'security', 'sales', 'inventory', 'config'
    action: str    # 'USER_CREATED', 'PRICE_CHANGE', etc.
    actor_uuid: str
    actor_name: str
    target_id: str # ID del objeto afectado (User ID, Order ID, Product ID)
    target_type: str # 'user', 'order', 'product'
    
    # El corazón de la auditoría global:
    changes_json: Optional[str] # JSON con {"old": ..., "new": ...}
    
    reason: Optional[str]
    timestamp: datetime
```

---

## 4. Hoja de Ruta de Implementación

### Fase A: Auditoría de Usuarios y Seguridad (Alta Prioridad)
1.  Modificar el modelo `AuditLog` para incluir `category` y `changes_json`.
2.  Actualizar `omni_auth` para registrar inicios de sesión y cambios en usuarios.
3.  Implementar el log de "Permiso Denegado" en el middleware de seguridad.

### Fase B: Auditoría de Precios e Inventario
1.  Hook en el servicio de inventario para registrar cambios de precios.
2.  Registro de ajustes manuales de stock.

### Fase C: Dashboard de Auditoría (Admin UI)
1.  Crear una vista de "Timeline" en el panel de administración de SvelteKit.
2.  Filtros por fecha, empleado y categoría.
3.  Exportación a PDF/Excel para reportes gerenciales.

---

## 5. Próximos Pasos Sugeridos
¿Te gustaría que comencemos modificando el modelo de base de datos para soportar estas nuevas categorías?
