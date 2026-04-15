import { page } from '$app/state';
import { ROLE_PRESETS_JS } from '$lib/roles';

export const appState = $state({
    currentTheme: 'corporate',
    isLoggedIn: false,
    cart: [] as any[],
    activeTable: null as any | null,
    activeOrder: null as any | null,
    activeShift: null as any | null,
    // Usuario autenticado
    userRole: null as string | null,
    userName: null as string | null,
    userUuid: null as string | null,
    permissions: {} as Record<string, boolean>,
    permissionsLoaded: false,  // true una vez que initAuth() terminó
});

export function setTheme(theme: string) {
    appState.currentTheme = theme;
    if (typeof document !== 'undefined') {
        document.documentElement.setAttribute('data-theme', theme);
    }
}

export function setAuth(status: boolean) {
    appState.isLoggedIn = status;
    if (!status) {
        appState.userRole = null;
        appState.userName = null;
        appState.userUuid = null;
        appState.permissions = {};
        appState.permissionsLoaded = false;
        // Limpiar cache de usuario al cerrar sesión
        if (typeof localStorage !== 'undefined') {
            localStorage.removeItem('X-Omni-Username');
            localStorage.removeItem('X-Omni-Role');
            localStorage.removeItem('X-Omni-Token');
        }
    }
}

/**
 * Llama a /_auth/me y carga el perfil real del usuario con sus permisos efectivos
 * (preset del rol + overrides individuales). Llamar en onMount del layout principal.
 */
export async function initAuth(): Promise<boolean> {
    const ls = typeof localStorage !== 'undefined' ? localStorage : null;
    const token = ls?.getItem('X-Omni-Token') ?? null;

    // Sin token → no autenticado
    if (!token) {
        appState.isLoggedIn = false;
        appState.permissionsLoaded = true;
        return false;
    }

    // ── Paso 1: token existe → asumir logueado de inmediato ──────────────────
    // Tomamos lo que hay en caché; si no hay nada, usamos defaults de admin
    const cachedUser = ls?.getItem('X-Omni-Username') ?? null;
    const cachedRole = ls?.getItem('X-Omni-Role') ?? 'admin';

    appState.isLoggedIn   = true;
    appState.userName     = cachedUser ?? 'Usuario';
    appState.userRole     = cachedRole;
    // Aplicar preset del rol inmediatamente — el nav funciona antes del fetch
    appState.permissions  = { ...(ROLE_PRESETS_JS[cachedRole] ?? ROLE_PRESETS_JS['admin']) };
    appState.permissionsLoaded = true;   // ← nav ya renderiza correctamente

    // ── Paso 2: verificar con el servidor y refinar permisos ─────────────────
    try {
        const res = await fetch('/api/_auth/me', { headers: { 'X-Omni-Token': token } });

        if (!res.ok) {
            // Token inválido → cerrar sesión y limpiar
            appState.isLoggedIn  = false;
            appState.permissions = {};
            ls?.removeItem('X-Omni-Token');
            ls?.removeItem('X-Omni-Username');
            ls?.removeItem('X-Omni-Role');
            return false;
        }

        const data = await res.json();
        appState.isLoggedIn  = true;
        appState.userRole    = data.role     ?? cachedRole;
        appState.userName    = data.username ?? cachedUser ?? 'Usuario';
        appState.userUuid    = data.uuid     ?? null;
        // Permisos del servidor (incluye overrides individuales guardados en metadata)
        appState.permissions = data.permissions ?? appState.permissions;

        // Actualizar caché con datos frescos
        ls?.setItem('X-Omni-Username', appState.userName ?? '');
        ls?.setItem('X-Omni-Role',     appState.userRole ?? '');
        return true;
    } catch {
        // Sin red → seguimos con el preset ya aplicado en Paso 1
        return false;
    }
}


// ── Etiquetas legibles por rol ──────────────────────────────────────────────
export const ROLE_LABELS: Record<string, string> = {
    admin:    'Administrador',
    manager:  'Gerente',
    cashier:  'Cajero/a',
    kitchen:  'Cocina',
    waiter:   'Mesero/a',
    operator: 'Administrador',  // alias legacy
};

export function getRoleLabel(role: string | null): string {
    if (!role) return '';
    return ROLE_LABELS[role] ?? role;
}

// Usar en cualquier componente Svelte:
// import { can } from '$lib/app_state.svelte';
export const can = {
    takeOrders:          () => appState.permissions['can_take_orders']           ?? false,
    sendToKitchen:       () => appState.permissions['can_send_to_kitchen']        ?? false,
    charge:              () => appState.permissions['can_charge']                 ?? false,
    manageKitchenStatus: () => appState.permissions['can_manage_kitchen_status']  ?? false,
    viewOrders:          () => appState.permissions['can_view_orders']            ?? false,
    manageTables:        () => appState.permissions['can_manage_tables']          ?? false,
    viewKitchen:         () => appState.permissions['can_view_kitchen']           ?? false,
    manageMenu:          () => appState.permissions['can_manage_menu']            ?? false,
    manageInventory:     () => appState.permissions['can_manage_inventory']       ?? false,
    manageUsers:         () => appState.permissions['can_manage_users']           ?? false,
    manageShifts:        () => appState.permissions['can_manage_shifts']          ?? false,
    viewReports:         () => appState.permissions['can_view_reports']           ?? false,
};

export function setActiveShift(shift: any | null) {
    appState.activeShift = shift;
}

export function addToCart(product: any, modifiers: any[] = [], variant?: any) {
    const basePrice = variant ? variant.price : product.price;
    const modifierTotal = modifiers.reduce((acc, m) => acc + (m.extra_price || 0), 0);
    const itemName = variant ? `${product.name} (${variant.measure?.name})` : product.name;

    const item = {
        id: Math.random().toString(36).substr(2, 9), // Unique ID for this specific cart instance
        product_id: product.id,
        product_variant_id: variant?.id,
        measure_id: variant?.measure_id,
        name: itemName,
        base_price: basePrice,
        modifiers: modifiers,
        quantity: 1,
        total_price: basePrice + modifierTotal
    };
    appState.cart = [...appState.cart, item];
}

export function removeFromCart(itemId: string) {
    appState.cart = appState.cart.filter(i => i.id !== itemId);
}

export function clearCart() {
    appState.cart = [];
}

export function setActiveTable(table: any | null, order: any | null = null) {
    appState.activeTable = table;
    appState.activeOrder = order;
    if (!table && !order) {
        appState.activeOrder = null;
    }
}

export function loadOrderToCart(order: any) {
    appState.cart = [];
    appState.activeOrder = order;
    
    if (order.items) {
        appState.cart = order.items.map((item: any) => {
            const variant = item.variant;
            const product = item.product || { name: `Producto #${item.product_id}` };
            
            // Construct name similarly to addToCart
            const measureName = variant?.measure?.name || variant?.measure;
            const itemName = measureName ? `${product.name} (${measureName})` : product.name;
            
            return {
                id: `db-${item.id}`, // Mark as coming from DB
                db_id: item.id,
                product_id: item.product_id,
                product_variant_id: item.product_variant_id,
                name: itemName,
                base_price: item.unit_price - (item.modifiers?.reduce((acc: number, m: any) => acc + (m.extra_price || 0), 0) || 0),
                modifiers: item.modifiers || [],
                quantity: item.quantity,
                total_price: item.unit_price * item.quantity,
                status: item.status
            };
        });
    }

    if (order.table_id) {
        // En un sistema real, buscaríamos el objeto mesa completo. 
        // Por ahora, creamos un objeto minimalista para la UI.
        appState.activeTable = { id: order.table_id, number: order.table_id };
    } else {
        appState.activeTable = null;
    }
}
