# 📋 Plan: Estrategia de Caché y Sincronización de Clientes (Distribuido)

Este documento define cómo Blackshot gestionará los datos de clientes en un entorno distribuido, optimizando el almacenamiento local y garantizando que los datos estén disponibles incluso offline para clientes frecuentes.

## 🎯 Objetivo
Evitar que las bases de datos locales (SQLite) de cada sucursal crezcan indefinidamente con datos de clientes que no son frecuentes en esa ubicación, manteniendo siempre un respaldo maestro en el Panel Central.

---

## 🛠️ Arquitectura de la Caché Local

### 1. Modelo de Datos de Cliente (`Customer`)
Cada registro local tendrá metadatos de sincronización:
- `last_visit_at`: Timestamp de la última transacción en la sucursal.
- `is_synced`: Booleano que indica si los cambios locales ya están en el Panel Central.
- `local_ttl`: Fecha de "expiración" sugerida para el registro local.

### 2. Flujo de Identificación (El Bridge)
Cuando un cliente llega a una sucursal:
1.  **Búsqueda Local**: Se busca en la DB de la sucursal (por ID, Email o Teléfono).
2.  **Búsqueda Remota (Bridge)**: Si no está local y hay internet, el Bridge consulta al Panel Central.
3.  **Hidratación Local**: Si el Panel Central lo encuentra, se descarga el perfil y se crea una copia local.
4.  **Modo Offline**: Si no hay internet y no está local, se crea un "Perfil Temporal" que se fusionará con el central cuando vuelva la conexión.

---

## 🧹 Estrategia de Limpieza (Purge Logic)

Para mantener la base de datos esbelta, se implementará un proceso automático:

| Criterio | Acción |
| :--- | :--- |
| **Cliente Frecuente** (Visita < 90 días) | Mantener en base local. |
| **Cliente Esporádico** (Visita > 90 días) | Si `is_synced == True`, eliminar de base local. |
| **Datos Transaccionales** | Las ventas NUNCA se eliminan localmente (son la base de los reportes Z), solo el perfil del cliente se "deshidrata". |

---

## 🔗 Integración con Autenticación

- Los **Clientes** NO se autentican contra la tabla `User` del Staff.
- Usarán un sistema de identificación simplificado (QR, Teléfono + PIN) gestionado por un servicio separado para evitar conflictos con la seguridad del personal operativo.

---

## ✅ Beneficios
1.  **Escalabilidad**: El sistema puede manejar millones de clientes a nivel global sin ralentizar las tablets/computadoras de una sucursal pequeña.
2.  **Privacidad Local**: Cada sucursal solo tiene los datos de las personas que realmente la visitan.
3.  **Resiliencia**: Los clientes frecuentes siempre están disponibles offline.
