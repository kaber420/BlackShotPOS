# 🚀 Blackshot POS: ROADMAP V2

Este roadmap marca la transición de un MVP local a un sistema profesional, seguro y listo para operaciones del mundo real.

---

## 🛡️ Fase 1: Identidad y Seguridad (Infraestructura)
Esta fase es crítica para exponer el sitio a internet sin riesgos innecesarios.
- [ ] **Migración a Kinde Auth**: Implementar autenticación gestionada (ver `docs/STRATEGY_AUTH_KINDE.md`).
- [ ] **Endurecimiento de API**: Implementar *Rate Limiting* y validación estricta de CORS.
- [ ] **Contenerización**: Crear `Dockerfile` y `docker-compose.yml` para un despliegue reproducible.

## 📊 Fase 2: Control Operativo y Finanzas
Funciones necesarias para que el dueño del negocio pueda confiar en los números del sistema.
- [ ] **Cierre de Caja (Z-Report)**:
    - Registro de apertura y cierre con montos de efectivo.
    - Reporte de ventas totales, por método de pago y variaciones.
- [ ] **Panel de Analíticas**:
    - Ranking de productos más vendidos.
    - Gráficas de ventas por horas/días.
- [ ] **Gestión de Cancelaciones**: Sistema de auditoría para pedidos cancelados o reembolsos.

## 🎁 Fase 3: Fidelización Digital (Sin Costos Externos)
Fortalecer la relación con los clientes sin pagar membresías de Apple/Google.
- [ ] **Sistema de Puntos Web (PWA)**:
    - Portal del cliente en `/fidelidad`.
    - Generación de código QR único por cliente.
- [ ] **Integración en POS**:
    - Escaneo de QR del cliente desde la pantalla de venta.
    - Aplicación automática de descuentos y suma de puntos por compra.
- [ ] **Wallet Manual**: Botón en la PWA para descargar el QR como imagen o "Añadir a pantalla de inicio".

## ⚡ Fase 4: Experiencia y Desempeño
Mejorar la velocidad de servicio y la interacción en el local.
- [ ] **Comunicación en Tiempo Real**:
    - Integración de WebSockets/SSE para que la cocina reciba órdenes sin refrescar la página.
- [ ] **Soporte de Impresión**:
    - Lógica para enviar tickets de venta y comandas a impresoras térmicas (formato ESC/POS).
- [ ] **UI Móvil para Meseros**:
    - Optimización de la interfaz de "Mesas" para uso fluido en teléfonos o tablets pequeñas.

---

## 📝 Notas de Versión
*   **V1 (Actual)**: Inventario, Gestión de Productos, Mesas y Órdenes Básicas.
*   **V2 (Objetivo)**: Seguridad SaaS, Operaciones Financieras y Fidelización.
