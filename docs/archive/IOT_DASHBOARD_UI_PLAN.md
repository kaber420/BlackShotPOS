# Plan Maestro: Blackshot IoT Table Dashboard

Este documento define la arquitectura visual y funcional definitiva para los dispositivos IoT instalados en las mesas del restaurante.

## 1. Visión del Producto
El dispositivo debe actuar como un centro de información y servicio "Zero-Friction" para el comensal, permitiéndole monitorear su pedido en tiempo real y solicitar asistencia sin interrumpir su experiencia.

## 2. Componentes de Interfaz (UI)

### A. Listado de Órdenes Dinámico
- **Visualización**: Tarjetas horizontales (estilo KDS) con los platos activos de la mesa.
- **Indicadores de Progreso**: Cada ítem debe incluir una `lv_bar` (barra de progreso) que refleje el porcentaje de preparación enviado desde el POS.
- **Estados de Color**:
    - *Preparando*: Verde neón (BS_COLOR_PRIMARY).
    - *Listo / Por Entregar*: Azul cian (BS_COLOR_ACCENT) con efecto de resplandor.
    - *Entregado*: Se elimina de la vista principal transcurridos 30 segundos.

### B. Menú de Acciones Escalable
- **Activador**: Un botón "ACCIONES" ubicado en la zona inferior (footer).
- **Acciones Disponibles (Overlay/Menú)**:
    - **🙋‍♂️ Solicitar Mesero**: Envía evento `call_waiter`.
    - **🧾 Solicitar Cuenta**: Envía evento `request_bill`.
    - **🥤 Rellenar Bebida** (Opcional futuro).

### C. Branding y Estado (Header)
- Nombre del negocio dinámico (Sync desde POS).
- Reloj digital en tiempo real.
- Status de conexión y batería.

## 3. Arquitectura Técnica (C++/LVGL)
- **Motor**: LVGL 9.x.
- **Modularidad**: El SDK debe ser agnóstico al tema, permitiendo cambiar entre este Dashboard y otros temas (como el Chibi) mediante configuración remota.
- **Responsividad**: Uso estricto de porcentajes y layouts `Flex` para soportar diferentes dimensiones de pantalla física.

## 4. Roadmap de Desarrollo
### Fase 1: Dashboard de Seguimiento y Servicio (Actual)
- Implementar tarjetas con barra de progreso.
- Panel de acciones (Mesero/Cuenta).
- Sincronización básica de estados.

### Fase 2: Menú de Auto-Pedido (Pantallas Grandes / Tablets)
- **Visualización**: Navegación por categorías de productos.
- **Interacción**: Selección de variantes y modificadores.
- **Integración**: Creación de órdenes directamente desde el IoT hacia el API de ventas del POS.
- **Pago**: Opción de pago con QR (PIX/Tarjeta) directamente en pantalla.

## 5. Próximos Pasos Inmediatos
1. Crear la clase `ThemeDashboard` en el SDK.
2. Implementar el generador de tarjetas con barra de progreso.
3. Desarrollar el sistema de menú de acciones tipo "Pop-up".
4. Integrar los nuevos eventos de WebSocket (`request_bill`).
