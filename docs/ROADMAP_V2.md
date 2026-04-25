# 🚀 Blackshot POS: ROADMAP V2

Este roadmap marca la transición de un MVP local a un sistema profesional, seguro y listo para operaciones del mundo real, cubriendo todas las necesidades de restaurantes y cafeterías modernas.

---

## 🛡️ Fase 1: Identidad y Seguridad (Infraestructura)
Esta fase es crítica para exponer el sitio a internet sin riesgos innecesarios.
- [ ] **Migración a Logto Auth**: Implementar autenticación gestionada y self-hosted (ver `docs/STRATEGY_AUTH_LOGTO.md`).
- [ ] **Endurecimiento de API**: Implementar *Rate Limiting* y validación estricta de CORS.
- [ ] **Contenerización**: Crear `Dockerfile` y `docker-compose.yml` para un despliegue reproducible.

## 📊 Fase 2: Control Operativo y Finanzas
Funciones necesarias para que el dueño del negocio pueda confiar ciegamente en los números del sistema y evitar fugas de capital.
- [ ] **Cierre de Caja (Z-Report) y Arqueo**:
    - **Fondo de Caja**: Declaración del monto inicial al abrir el turno.
    - **Arqueo Ciego**: El cajero debe ingresar cuánto efectivo tiene físicamente antes de que el sistema le revele cuánto debería haber.
    - **Reporte Detallado**: Desglose de ingresos por método de pago, propinas separadas del ingreso neto, y registro de sobrantes/faltantes.
- [ ] **Módulo de Pagos Avanzados**:
    - **Cuentas Separadas (Split Bill)**: Flexibilidad total. Dividir por porcentaje (ej. 50/50), por monto fijo, por "asientos" o permitiendo seleccionar qué productos paga cada comensal. Incluso permitir dividir el costo de un solo producto entre varias personas.
    - **Pagos Mixtos**: Capacidad de liquidar un ticket usando múltiples métodos simultáneamente (ej. $100 en efectivo, $250 en tarjeta y $50 en transferencia), calculando automáticamente el cambio aplicable solo a la porción de efectivo.
    - **Gestión de Propinas (Tip Management)**: Captura del porcentaje o monto de propina (común en terminales de tarjeta). Contabilidad separada para que el sistema calcule el "pago de propinas" al personal al final del turno.
- [ ] **Panel de Analíticas y Control de Costos**:
    - Dashboard de ventas en tiempo real (por hora, por día, por mes).
- [ ] **Gestión de Cancelaciones y Mermas (Waste Management)**:
    - **Mermas**: Permite a los gerentes descargar ingredientes del inventario por caducidad, accidentes (ej. un café derramado) o errores, manteniendo un registro justificado.
    - **Auditoría de Cancelaciones**: Todo reembolso o platillo eliminado de una cuenta activa requiere autorización y genera un log de auditoría inmutable.

## 🎁 Fase 3: Fidelización Digital (Sin Costos Externos)
Fortalecer la relación con los clientes construyendo una base de datos propia (CRM).
- [ ] **Sistema de Puntos Web (PWA)**: Portal en `/fidelidad` para el cliente.
- [ ] **Generación y Escaneo de QR**: Identificador único por cliente para escanear en el POS, sumando puntos automáticamente y aplicando descuentos por lealtad.
- [ ] **Wallet Manual**: Botón en la PWA para descargar el QR como imagen.

## ⚡ Fase 4: Experiencia, Desempeño y Tolerancia a Fallos
Asegurar que la operación en piso sea ultrarrápida y resistente a problemas técnicos.
- [x] **Comunicación en Tiempo Real**: WebSockets/SSE para la cocina.
- [x] **Soporte de Impresión Térmica**: Protocolo ESC/POS.
- [ ] **Toma de Pedidos Móvil (UI Meseros)**:
    - Rediseño de la cuadrícula de mesas y el flujo del carrito para ser operados con una sola mano en pantallas de 6 a 8 pulgadas, usando botones grandes y deslizamientos (swipes).
- [ ] **Eficiencia en KDS (Kitchen Display System)**:
    - Filtros por "Estación" (ej. Pantalla de Barra de Bebidas vs Pantalla de Parrilla).
    - **SLA Visual**: Las comandas cambian de color (verde -> amarillo -> rojo parpadeante) basado en temporizadores de preparación (ej. rojo tras 15 minutos).
- [ ] **Modo Offline (Resiliencia de Red)**:
    - Implementación de un Service Worker que cachee la aplicación.
    - Cola de sincronización local (IndexedDB): Si se cae el internet local, los meseros pueden seguir tomando comandas y cerrando ventas en efectivo. El sistema guarda las transacciones y las envía automáticamente al servidor al recuperar la conexión.

## 🍽️ Fase 5: Operaciones Avanzadas y Gestión de Flujo
Expansión hacia un sistema integral para restaurantes de alto tráfico.
- [ ] **Gestión de Reservaciones, Mesas y Lista de Espera**:
    - **Timeline Visual**: Un calendario interactivo para ver la ocupación por horas.
    - **Reglas de Bloqueo**: Impedir que un mesero ocupe físicamente una mesa que está a 30 minutos de recibir una reservación.
    - **Lista de Espera (Waitlist)**: Registro rápido de tamaño de grupo y nombre. El sistema calcula un tiempo de espera estimado y permite notificar (visualmente o futuro SMS) cuando la mesa esté lista.
    - **Estados de Mesa Extendidos**: Libre, Ocupada (comiendo), Esperando Pago, Sucia (por limpiar), Reservada.
- [ ] **Nuevos Canales: Delivery y Takeout (Para Llevar)**:
    - Flujo de pedido especializado que captura Nombre, Teléfono, y Plataforma (ej. Uber, Didi, Pick-up local).
    - Indicadores especiales en los tickets de cocina para usar empaques desechables en lugar de loza.
    - Control de estados: "En preparación" -> "Listo para recolección" -> "Entregado".


---

## 📝 Notas de Versión
*   **V1 (Actual)**: Inventario, Gestión de Productos, Mesas y Órdenes Básicas.
*   **V2 (Objetivo)**: Seguridad, Control Financiero Estricto, Resiliencia y Funciones Profesionales para Restaurantes.
