# Plan de Optimización y Robustez: Módulo `pos_core/catalog`

Este documento detalla un análisis del estado actual del módulo `pos_core/catalog` y propone mejoras específicas para optimizar el rendimiento, fortalecer la robustez y mejorar la arquitectura del código.

## 1. Arquitectura y Separación de Responsabilidades

### 1.1 Limpieza de Controladores (`router.py` vs `services`)
**Hallazgo:** Actualmente, los endpoints de rutas para recetas (`add_ingredient_to_recipe`, `add_ingredient_to_variant`) incluyen lógica de negocio de conversión de unidades directamente en el controlador (`router.py`), accediendo a la base de datos (e.g. `await db.get(Ingredient, ingredient_id)`). En contraste, en `modifier_service.py`, esta lógica de conversión sí está dentro de la capa de servicio.
**Propuesta:** 
* Mover toda la lógica de validación y conversión de unidades desde `router.py` hacia los servicios correspondientes (`recipe_service.py`).
* Mantener los controladores "delgados" (thin controllers) limitados únicamente a validar inputs HTTP y delegar la lógica de negocio a la capa de servicio.

### 1.2 Extracción de Gestión de Medios
**Hallazgo:** Los endpoints `/upload` y `/upload/{filename}` están incrustados en el router de catalog (`router.py`).
**Propuesta:** 
* Mover la gestión de subida y eliminación de imágenes a un módulo o enrutador dedicado a archivos (`pos_core/media/router.py` o similar). El catálogo solo debería preocuparse por almacenar la URL de la imagen, no de la manipulación de archivos físicos del sistema.

## 2. Rendimiento y Consultas de Base de Datos (SQLModel/SQLAlchemy)

### 2.1 Eager Loading Excesivo (`category_service.py`)
**Hallazgo:** La función `get_categories` utiliza un `selectinload` muy profundo para cargar no solo las categorías, sino todos los productos asociados con sus impuestos, variantes, medidas, grupos de modificadores, modificadores e ingredientes.
```python
statement = select(Category).options(
    selectinload(Category.products).options(
        selectinload(Product.tax),
        selectinload(Product.variants).joinedload(ProductVariant.measure),
        selectinload(Product.modifier_groups)...
```
**Problema:** A medida que crezca el catálogo, llamar a la ruta `/categories` (que llama a esta función) serializará y transferirá una enorme cantidad de datos innecesarios a la memoria y por la red, causando cuellos de botella de rendimiento.
**Propuesta:** 
* Dividir en dos tipos de consulta: un `get_categories` ligero que solo traiga metadatos de las categorías, y permitir que los productos de una categoría se consulten a través de paginación o mediante el endpoint existente `/products?category_id=X`.
* Si el frontend requiere la carga total por razones de offline-first, al menos optimizar la respuesta implementando caché (Redis/Memcached) o estrategias de sincronización más eficientes.

## 3. Integridad de Datos y Validaciones (`models.py`)

### 3.1 Constraints de Base de Datos (CheckConstraints)
**Hallazgo:** Campos como `price`, `quantity`, `stock`, `calories`, etc., usan el tipo `float` o `int` sin restricciones de negatividad a nivel de base de datos o de Pydantic.
**Propuesta:**
* Agregar restricciones con `Field(ge=0)` de Pydantic en los esquemas `*Create` y `*Update` para validar antes de insertar a base de datos.
* Opcionalmente, agregar `CheckConstraint('price >= 0')` en los modelos SQLAlchemy para garantizar la integridad a nivel de base de datos.

### 3.2 Modelos de Respuesta Completos
**Hallazgo:** Existen modelos como `RecipeItem` que se retornan de manera directa sin un modelo intermedio `RecipeItemRead`. 
**Propuesta:** 
* Consolidar siempre el patrón de crear el modelo Pydantic `*Read` para las salidas en la API y asegurar de esconder o estructurar datos sensibles/internos si los hubiere, y normalizar las relaciones.

## 4. Prácticas Generales de Ingeniería

### 4.1 Manejo de Excepciones Constantes
**Hallazgo:** Si se intenta crear un modelo (ej. `Product`) con un SKU duplicado, la base de datos lanzará un `IntegrityError` que FastAPI capturará como un `500 Internal Server Error`, exponiendo fallos genéricos al usuario.
**Propuesta:** 
* Capturar `sqlalchemy.exc.IntegrityError` en los servicios o mediante un exception handler global en FastAPI para retornar un `400 Bad Request` semántico ("Ya existe un producto con este SKU o Nombre").

### 4.2 Eliminación de Rutas y Configuraciones "Hardcodeadas"
**Hallazgo:** El directorio `"data/img"` para guardado y eliminación de imágenes se escribe literalmente en varios archivos (`router.py`, `services/utils.py`).
**Propuesta:** 
* Centralizar las rutas en un archivo de configuración dependiente de variables de entorno (como `config.py` con `pydantic-settings`), lo cual asegura flexibilidad si se mueve la carpeta a un S3 u otro storage en el futuro.

## Resumen de Tareas Sugeridas
1. Refactorizar `recipe_service.py` y `router.py` para aislar lógica de negocio.
2. Mover endpoints de archivos multimedia.
3. Alivianar carga de relaciones en `get_categories`.
4. Agregar restricciones `>= 0` en Modelos.
5. Controlar errores de integridad en servicios de creación.
