# Plan de Implementación: Carritos Múltiples y Pausado (Multi-Session POS)

Este plan detalla cómo evolucionar el sistema de carrito único a un sistema multi-sesión que permita a los cajeros manejar múltiples clientes simultáneamente (ej. pausar Mesa 1 para atender Mesa 2).

## 1. Objetivo
Permitir que el estado del carrito sea independiente por mesa o por "ticket abierto", de modo que al cambiar de mesa no se pierdan los artículos agregados, sino que se "pausen" automáticamente.

## 2. Cambios en el Estado Global (`appState`)

Actualmente `appState` tiene un único `cart`. El cambio propuesto es mover los carritos a un diccionario de sesiones.

```typescript
// Estructura propuesta
export const appState = $state({
    // ...
    activeTableId: null as number | null,
    sessions: {} as Record<number | string, {
        cart: any[],
        activeOrder: any | null,
        timestamp: number
    }>,
    // El cart actual sería un $derived de la sesión activa
    get currentCart() {
        return this.sessions[this.activeTableId]?.cart || [];
    }
});
```

## 3. Flujo de Usuario (UX)

1.  **Inicio:** El cajero selecciona la **Mesa 1**.
2.  **Acción:** Agrega 2 Cafés. El sistema guarda esto en `sessions[1]`.
3.  **Pausa/Cambio:** El cajero hace clic en **Mesa 2** (o un botón de "Nueva Orden").
4.  **Auto-Guardado:** El sistema detecta el cambio de ID, mantiene los Cafés en la sesión 1 y limpia la vista principal para la **Mesa 2**.
5.  **Retorno:** El cajero vuelve a la **Mesa 1**. El sistema recupera el carrito con los 2 Cafés instantáneamente.

## 4. Persistencia en LocalStorage

Se actualizará `persistSession` para guardar el objeto `sessions` completo.

*   **Regla de Limpieza:** Las sesiones pausadas que tengan más de 2 horas de inactividad se eliminarán automáticamente para no saturar el almacenamiento.
*   **Sincronización:** Al cargar, se recuperarán todas las sesiones activas.

## 5. Interfaz de Usuario (UI)

*   **Indicador de Actividad:** En el mapa de mesas, las mesas que tengan un "carrito pausado" mostrarán un pequeño icono de carrito o un color distinto (ej. naranja para "En proceso", rojo para "Ocupada/Enviada a cocina").
*   **Barra de Sesiones:** Una pequeña barra lateral o pestañas que permitan ver rápidamente qué carritos están "abiertos" sin necesidad de ir al mapa de mesas.
*   **Botón "Pausar":** En el Drawer del carrito, un botón para des-seleccionar la mesa actual sin perder los datos.

## 6. Pasos de Implementación

1.  **Fase 1 (Data):** Refactorizar `app_state.svelte.ts` para usar `sessions` en lugar de un único `cart`.
2.  **Fase 2 (Logic):** Modificar `setActiveTable` para que realice el "swap" de carritos automáticamente.
3.  **Fase 3 (UI):** Actualizar el componente `FloatingCart` y `TableMap` para reflejar el estado de las sesiones pausadas.
4.  **Fase 4 (API):** (Opcional) Sincronizar estos carritos pausados con el backend como "Draft Orders" para que sean visibles en otros dispositivos.

---
**Nota:** Este sistema soluciona el problema de los clientes indecisos ("espéreme tantito") sin bloquear el flujo de la caja.
