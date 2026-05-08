# Draft: Arquitectura Postgres + Módulos Autónomos (EDA)

## 1. Visión General
Este documento define la transición de una arquitectura centralizada (Global Persistence Worker) hacia un modelo descentralizado de **Módulos Autónomos** aprovechando la capacidad de concurrencia nativa de **PostgreSQL**.

## 2. El Cambio de Motor: SQLite -> PostgreSQL
- **Razón**: SQLite presenta bloqueos (`Database is locked`) ante escrituras concurrentes de múltiples terminales.
- **Solución**: Postgres permite que múltiples procesos y hilos escriban simultáneamente sin bloqueos de archivo.

## 3. Descentralización de la Persistencia
Se elimina el concepto de "Global Persistence Worker" (GPW). Cada módulo ahora es responsable de su propia escritura en la base de datos.

### 3.1. Flujo de Ejecución
1.  **Módulo Origen (ej. Ventas)**: Realiza la acción principal, guarda en DB y publica un evento.
2.  **Internal Event Bus**: Despacha el mensaje a todos los suscriptores interesados.
3.  **Módulos Destino (ej. Inventario, Contabilidad)**: Reciben el evento y ejecutan su propia persistencia en Postgres de forma independiente.

## 4. El Bus de Eventos Interno (`InternalEventBus`)
Se implementará un despachador ligero basado en `asyncio.Queue` para asegurar que los "Efectos Secundarios" no bloqueen la respuesta al usuario.

## 5. Pasos Técnicos para el Plan de Acción
1.  Migración de Driver: Cambiar `aiosqlite` por `asyncpg`.
2.  Configuración de Engine: Optimizar el pool de conexiones en `database.py`.
3.  Implementación del Bus: Crear la clase `InternalEventBus`.
4.  Refactorización de Listeners: Mover la lógica de descuento de stock y contabilidad a suscriptores autónomos.
