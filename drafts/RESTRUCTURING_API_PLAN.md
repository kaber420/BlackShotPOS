# Plan de Reestructuración de API y Frontend

Este documento detalla los cambios necesarios para separar limpiamente los dominios de Catálogo e Inventario, asegurando que cada uno tenga su propio prefijo de URL y que el Frontend se sincronice correctamente.

## 1. Cambios en Backend (main.py)

Se asignarán prefijos específicos para evitar colisiones y mantener una estructura profesional:

| Router | Prefijo Nuevo | Tags |
| :--- | :--- | :--- |
| `catalog_router` | `/api/v1/pos/catalog` | Catálogo |
| `inventory_router` | `/api/v1/pos/inventory` | Inventario |
| `production_area_router` | `/api/v1/pos/catalog/production` | Producción |

## 2. Cambios en Frontend (API Clients)

Se actualizarán las rutas en los archivos de `/src/lib/api/` para coincidir con el backend:

### src/lib/api/products.ts
- `/api/v1/pos/products` -> `/api/v1/pos/catalog/products`
- `/api/v1/pos/categories` -> `/api/v1/pos/catalog/categories`
- `/api/v1/pos/measures` -> `/api/v1/pos/catalog/measures`
- `/api/v1/pos/variants` -> `/api/v1/pos/catalog/variants`
- `/api/v1/pos/modifier-groups` -> `/api/v1/pos/catalog/modifier-groups`
- `/api/v1/pos/modifiers` -> `/api/v1/pos/catalog/modifiers`
- `/api/v1/pos/upload` -> `/api/v1/pos/catalog/upload`

### src/lib/api/ingredients.ts
- `/api/v1/pos/ingredients` -> `/api/v1/pos/inventory/ingredients`
- `/api/v1/pos/adjustments` -> `/api/v1/pos/inventory/adjustments`

## 3. Resolución de Errores en UI

- Se eliminarán los parches temporales en `admin/inventory/ingredients/+page.svelte`.
- Se restaurará la carga mediante `Promise.all` una vez que las rutas sean consistentes.
- Se reactivará la sincronización vía `posSocket` para el inventario.

## 4. Verificación

1. Reiniciar el servidor backend.
2. Abrir el POS y verificar la carga del menú.
3. Abrir el Maestro de Inventario y verificar que los insumos aparezcan correctamente.
