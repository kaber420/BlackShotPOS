# Propuesta: Registro Automático de Proveedores de Eventos (Auto-Discovery)

## 1. El Problema Actual
Actualmente, el sistema utiliza un archivo central `pos_core/events/setup.py` que debe importar manualmente cada módulo de la aplicación (`sales`, `tables`, `inventory`, etc.) para registrar sus proveedores de datos.

**Inconvenientes:**
*   **Mantenimiento tedioso:** Cada vez que se crea un nuevo módulo o tópico, hay que editar el archivo central.
*   **Dependencias Circulares:** Obliga a usar importaciones dentro de funciones para evitar que Python falle al arrancar.
*   **Código "Sucio":** El archivo central conoce detalles íntimos de todos los demás módulos, rompiendo el encapsulamiento.

## 2. Solución Propuesta: Auto-Discovery mediante Decoradores
Invertiremos la responsabilidad. En lugar de que el sistema de eventos "busque" a los módulos, los módulos se "anunciarán" a sí mismos.

### Componentes de la Solución

#### A. Decoradores de Registro
Añadiremos decoradores en `pos_core/events/registry.py` e `iot_registry.py`:
```python
@topic_provider("nombre_del_topico")
async def mi_proveedor(session): ...
```

#### B. Motor de Descubrimiento (`discovery.py`)
Un nuevo módulo que, al iniciar la aplicación:
1.  Escanea el directorio `pos_core/`.
2.  Busca archivos llamados `providers.py` (o cualquier archivo que contenga proveedores).
3.  Los importa dinámicamente. Al importarlos, los decoradores se ejecutan y llenan el registro automáticamente.

#### C. Punto de Entrada Limpio
En `main.py`, eliminaremos las importaciones manuales y usaremos una sola llamada:
```python
from pos_core.events.discovery import discover_event_providers

@asynccontextmanager
async def lifespan(app: FastAPI):
    ...
    discover_event_providers() # Encuentra todo automáticamente
    ...
```

## 3. Ventajas de este Enfoque
1.  **Modularidad Real:** Puedes añadir o quitar módulos (ej: `marketing`, `loyalty`) simplemente moviendo carpetas, sin tocar el núcleo de eventos.
2.  **Cero Circularidad:** Las dependencias siempre van del módulo hacia el sistema de eventos, nunca al revés.
3.  **Código más "Pythonic":** Sigue el patrón de frameworks modernos como FastAPI o Flask.
4.  **Menos Errores:** Evita olvidar registrar un tópico manualmente.

## 4. Pasos para la Implementación
1.  **Refactorizar `registry.py`**: Añadir la lógica del decorador.
2.  **Crear `discovery.py`**: Implementar el escaneo de paquetes usando `pkgutil`.
3.  **Actualizar Módulos**: Añadir los decoradores en `sales`, `tables`, `inventory`, `analytics` e `iot`.
4.  **Eliminar `setup.py`**: Limpiar el código antiguo.
5.  **Actualizar `main.py`**: Conectar el nuevo sistema.

---
**Estado:** Borrador (Draft)
**Autor:** Antigravity AI
**Fecha:** 2026-05-04
