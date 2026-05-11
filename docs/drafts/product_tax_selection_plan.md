# Plan de Implementación: Selección de Impuestos por Producto

Este documento describe los pasos para permitir elegir la tasa de impuesto al agregar o editar un producto desde el menú del POS (`bs_frontend`).

## Arquitectura y Flujo

Dado que el objetivo es gestionar el impuesto localmente desde el Menú del POS, se aprovechará la tabla `Tax` ya existente en la base de datos de la sucursal.

### 1. Backend API (`pos_core`)
La base de datos local ya posee la tabla `Tax`, pero la API no expone estos datos para el frontend.
- **`pos_core/catalog/services/product_service.py`**: Añadir la función `get_taxes(session)` para consultar la tabla `Tax` (usando `select(Tax).where(Tax.is_active == True)`). No olvidar importar `Tax`.
- **`pos_core/catalog/router.py`**: Añadir la ruta `GET /taxes` bajo el router de catálogo para retornar la lista de impuestos disponibles (`List[TaxRead]`). Asegurar importar `TaxRead`.
- **`pos_core/catalog/models.py`**: Validar que `TaxRead` está correctamente definido y exportado para el endpoint. `ProductUpdate` y `ProductCreate` ya incluyen `tax_id`.

### 2. Frontend API Client (`bs_frontend`)
- **`src/lib/api/products.ts`**: La interfaz `Tax` ya existe, pero hay que asegurarse de agregar `tax_id?: number;` a la interfaz `Product`. Luego, agregar el método `getTaxes: () => fetchApi<Tax[]>('/api/v1/pos/catalog/taxes')` a la clase `ProductService`.

### 3. Frontend Interfaz de Usuario (`bs_frontend`)
- **`src/lib/components/ProductModal.svelte`**: Al abrir el modal de edición/creación de producto (`loadData`), llamar a `ProductService.getTaxes()` para cargar la lista de impuestos disponibles (`taxes`). Pasar esta lista como propiedad (prop) al componente `ProductGeneralForm`.
- **`src/lib/components/product/ProductGeneralForm.svelte`**: Añadir `taxes: Tax[]` a las propiedades que recibe el componente. Añadir un menú desplegable (`<select>`) vinculando `formData.tax_id` con la lista de impuestos. Se incluirá una opción predeterminada (Ej. "Global" o "Sin impuesto específico" que mande el valor `undefined` o `null`).

## Dudas Pendientes / Tareas de Inicialización

> [!NOTE]
> **Datos Base (Sembrado):** Si la base de datos no tiene aún los registros de impuestos (0%, 8%, 16%), será necesario añadirlos mediante el script de *seed* (`scripts/seeds/seed_data.py`).

## Plan de Pruebas
1. Iniciar la API del POS local y asegurar que existen registros de impuestos en la DB.
2. Abrir el Frontend de administración del POS.
3. Navegar a la pestaña **Menú** -> **+ Producto** (o editar uno existente).
4. Verificar que el selector de "Impuesto" sea visible en la pestaña "General".
5. Seleccionar un impuesto específico (ej. 0%) y guardar el producto.
6. Añadir el producto a una orden de venta en el POS y confirmar que el cálculo de totales aplica la tasa del producto en lugar de la tasa global.
