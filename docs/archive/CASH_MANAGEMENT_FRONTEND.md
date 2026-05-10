# Cash Management Frontend - Technical Specification

Este documento detalla la experiencia de usuario y componentes para la sección de Cajas y Cortes.

## 1. Vistas y Navegación

### `RegisterSelection.svelte` (Vista Inicial)
Si el usuario no tiene un turno activo, se le muestra una cuadrícula de cajas disponibles.
- **Card de Caja**: Nombre, Estado (Abierta/Cerrada), Cajero actual (si está abierta).
- **Acción**: Si está cerrada, botón "Abrir Caja" que abre un modal para ingresar el fondo inicial.

### `AccountingDashboard.svelte` (Vista de Control)
Accesible desde el menú lateral para usuarios con permisos.
- **Resumen en Tiempo Real (Corte X)**:
    - Widget de Efectivo (Fondo + Ventas - Gastos).
    - Widget de Tarjetas.
    - Widget de Transferencias.
- **Lista de Movimientos**: Tabla con los ingresos y retiros realizados en el turno.
- **Botones de Acción**:
    - `[+] Ingreso`: Para fondos extra.
    - `[-] Retiro`: Para pagos a proveedores o retiros parciales de seguridad.
    - `[Imprimir Corte X]`: Envía reporte parcial a la impresora térmica.

## 2. Componentes Clave

### `CashCounter.svelte` (Ayudante de Cierre)
Un modal interactivo para ayudar al cajero a contar el dinero físico.
- Lista de denominaciones (Billetes: 1000, 500, 200, 100, 50, 20; Monedas: 10, 5, 2, 1).
- El usuario ingresa la cantidad de cada uno y el sistema calcula el total automáticamente.
- **Propósito**: Reducir errores humanos en el conteo manual.

### `CloseShiftModal.svelte`
- Paso 1: Contar Efectivo (usando `CashCounter`).
- Paso 2: Ingresar totales de voucher (Tarjetas).
- Paso 3: Resumen final de diferencias (Sobrante/Faltante).
- Paso 4: Confirmación y Cierre Z.

## 3. Gestión de Estado (App State)

Necesitamos trackear en `app_state.svelte.ts`:
- `activeShift`: El ID del turno actual.
- `currentRegister`: La caja que está operando el dispositivo actual.

## 4. Flujo de Usuario (UX)

1.  **Login**: El cajero entra al POS.
2.  **Selección**: El sistema detecta que no hay turno. Pide seleccionar "Caja Barra".
3.  **Apertura**: Ingresa $1,000 de fondo. Se abre el POS para vender.
4.  **Venta**: Durante el día, el cajero realiza un retiro de $300 para "Hielo".
5.  **Cierre**: Al final del día, pulsa "Cerrar Turno".
    - El sistema le pide contar el dinero.
    - El cajero cuenta $2,500.
    - El sistema dice: "Esperado: $2,500. Diferencia: $0".
    - El cajero confirma. Se imprime el ticket Z y se cierra la sesión.
