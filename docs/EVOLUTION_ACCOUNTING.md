# Evolución de Módulo: Contabilidad (Event-Driven)

## 1. Integración con el Bus de Eventos
El módulo de contabilidad automatizará el registro de flujos de caja y la auditoría de turnos basándose en los eventos financieros.

### Eventos Escuchados:
- `sales.payment_received`: Actualiza el saldo esperado en el cajón (Cash Register).
- `shift.opened / shift.closed`: Notifica a otros módulos para resetear estadísticas locales.
- `accounting.expense_registered`: Registra gastos de caja chica.

## 2. Beneficios
- **Precisión**: El saldo de caja se actualiza en tiempo real con cada pago, sin necesidad de llamadas manuales desde el router de ventas.
- **Integridad de Auditoría**: Cada movimiento contable queda vinculado al ID del evento que lo originó.
