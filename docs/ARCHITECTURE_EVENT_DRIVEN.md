# Especificación Maestro: Arquitectura Dirigida por Eventos (EDA)

## 1. Visión General
Esta especificación define la transición de Blackshot POS hacia un modelo de acoplamiento débil. El objetivo es eliminar las dependencias directas entre módulos (Ventas -> Inventario, Ventas -> Mesas) y sustituirlas por un flujo de mensajes asíncronos y seguros.

## 2. El Bus de Eventos Interno (`InternalEventBus`)

El corazón de esta arquitectura es un despachador centralizado que permite el patrón Pub/Sub dentro del servidor Python.

### 2.1. Definición Técnica
- **Inmutabilidad**: Una vez emitido, un evento no puede ser modificado.
- **Asincronía**: Los suscriptores (Listeners) no bloquean el flujo principal del API.
- **Aislamiento**: Un error en un suscriptor (ej: falla al descontar stock) no debe hacer que la venta falle, sino que debe ser manejado por reintentos o alertas de auditoría.

### 2.2. Anatomía de un Evento
```python
{
    "event_id": "uuid-v4",
    "topic": "sales.order_delivered",
    "payload": {
        "order_id": 123,
        "items": [...],
        "table_id": 5
    },
    "metadata": {
        "actor_uuid": "...",
        "timestamp": "2026-05-07T..."
    }
}
```

---

## 3. Estrategia de Implementación por Dominios

Hemos separado la aplicación de esta arquitectura en guías específicas para cada módulo del sistema:

### 3.1. Inventario (Prioridad P0)
Se utiliza un **Worker Centralizado** para serializar las escrituras y garantizar la integridad de los Lotes (FEFO).
- **Ver detalle**: [EVOLUTION_INVENTORY.md](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/docs/EVOLUTION_INVENTORY.md)

### 3.2. Mesas y Estado Operativo
Se desacopla la lógica de ocupación de la lógica financiera, permitiendo pagos parciales y anticipados.
- **Ver detalle**: [EVOLUTION_TABLES.md](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/docs/EVOLUTION_TABLES.md)

### 3.3. Ventas y Ciclo de Vida
El módulo de Ventas se convierte en un emisor puro de señales, eliminando el "cochinero" de importaciones circulares.
- **Ver detalle**: [EVOLUTION_SALES.md](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/docs/EVOLUTION_SALES.md)

### 3.4. Contabilidad y Auditoría
Automatización de flujos de caja y logs basada en la escucha pasiva de eventos.
- **Ver detalle**: [EVOLUTION_ACCOUNTING.md](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/docs/EVOLUTION_ACCOUNTING.md)

---

## 4. Estándares de Seguridad y Calidad
1. **Atenticidad**: Todo evento debe incluir el UUID del actor que lo originó.
2. **Logging**: El Bus de Eventos registrará cada mensaje emitido para facilitar el debugging.
3. **Idempotencia**: Los suscriptores deben ser capaces de manejar el mismo evento dos veces sin causar errores en los datos.

---
**Estado**: Especificación Maestro Aprobada para Planificación.
