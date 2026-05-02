import { page } from '$app/state';
import { ROLE_PRESETS_JS } from '$lib/roles';
import { SettingsService } from './api/settings';
import { fetchApi } from './api';

const SESSION_STORAGE_KEY = 'bs_pos_session';

function loadSavedSession() {
    if (typeof localStorage === 'undefined') return { cart: [], activeTable: null, activeOrder: null };
    try {
        const saved = localStorage.getItem(SESSION_STORAGE_KEY);
        if (!saved) return { cart: [], activeTable: null, activeOrder: null };
        const parsed = JSON.parse(saved);
        
        // Expiración: 1 hora (3600000 ms)
        const ONE_HOUR = 3600000;
        if (parsed.timestamp && (Date.now() - parsed.timestamp > ONE_HOUR)) {
            console.log("Sesión persistente expirada (> 1 hora).");
            localStorage.removeItem(SESSION_STORAGE_KEY);
            return { cart: [], activeTable: null, activeOrder: null };
        }

        return {
            cart: parsed.cart || [],
            activeTable: parsed.activeTable || null,
            activeOrder: parsed.activeOrder || null
        };
    } catch (e) {
        console.error("Error loading saved session", e);
        return { cart: [], activeTable: null, activeOrder: null };
    }
}

const savedSession = loadSavedSession();

export const appState = $state({
    currentTheme: 'corporate',
    isLoggedIn: false,
    cart: savedSession.cart,
    activeTable: savedSession.activeTable,
    activeOrder: savedSession.activeOrder,
    activeShift: null as any | null,
    // Usuario autenticado
    userRole: null as string | null,
    userName: null as string | null,
    userUuid: null as string | null,
    permissions: {} as Record<string, boolean>,
    permissionsLoaded: false,  // true una vez que initAuth() terminó
    settings: {
        name: 'Blackshot Coffee',
        tax_rate: 0.16,
        currency_symbol: '$',
        currency_code: 'MXN',
        locale: 'es-MX'
    } as any,
    cartVisible: false,
    suggestedPaymentAmount: 0,
    suggestedPeopleCount: 1,
});

/**
 * Guarda el estado crítico del POS (carrito, mesa, orden) en localStorage
 */
export function persistSession() {
    if (typeof localStorage === 'undefined') return;
    const sessionData = {
        cart: appState.cart,
        activeTable: appState.activeTable,
        activeOrder: appState.activeOrder,
        timestamp: Date.now()
    };
    localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(sessionData));
}

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
        // Limpiar session storage
        if (typeof localStorage !== 'undefined') {
            localStorage.removeItem(SESSION_STORAGE_KEY);
        }
    }
}

/**
 * Cierra la sesión tanto en el cliente como en el servidor.
 */
export async function logout() {
    try {
        await fetchApi('/api/auth/jwt/logout', { method: 'POST' });
    } catch (e) {
        console.error("Error al cerrar sesión en el servidor:", e);
    } finally {
        setAuth(false);
        if (typeof window !== 'undefined') {
            window.location.href = '/login';
        }
    }
}

/**
 * Llama a /api/users/me y carga el perfil real del usuario con sus permisos efectivos.
 * Llamar en onMount del layout principal.
 */
export async function initAuth(): Promise<boolean> {
    appState.permissionsLoaded = false;
    try {
        const data = await fetchApi<any>('/api/users/me');

        appState.isLoggedIn  = true;
        appState.userUuid    = data.id;
        appState.userName    = data.email.split('@')[0];
        
        const metadata = data.custom_metadata || {};
        appState.userRole    = metadata.role || 'waiter';
        
        const rolePreset = ROLE_PRESETS_JS[appState.userRole] || ROLE_PRESETS_JS['waiter'];
        appState.permissions = { ...rolePreset, ...(metadata.permissions || {}) };
        
        // Cargar configuración del negocio
        try {
            appState.settings = await SettingsService.get();
        } catch (e) {
            console.warn("Usando configuración por defecto (error en SettingsService)");
        }

        return true;
    } catch (error) {
        // 401 es normal si no ha iniciado sesión
        appState.isLoggedIn = false;
        return false;
    } finally {
        appState.permissionsLoaded = true;
    }
}



// ── Etiquetas legibles por rol ──────────────────────────────────────────────
export const ROLE_LABELS: Record<string, string> = {
    admin:    'Administrador',
    manager:  'Gerente',
    cashier:  'Cajero/a',
    kitchen:  'Cocina',
    waiter:   'Mesero/a',
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
    manageSettings:      () => appState.permissions['can_manage_settings']          ?? false,
    viewAudits:          () => appState.permissions['can_view_audits']          ?? false,
    manageIoT:           () => appState.permissions['can_manage_iot']          ?? false,
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
    persistSession();
}

export function removeFromCart(itemId: string) {
    appState.cart = appState.cart.filter(i => i.id !== itemId);
    persistSession();
}

export function updateCartItemQuantity(itemId: string, delta: number) {
    const index = appState.cart.findIndex(i => i.id === itemId);
    if (index === -1) return;

    const item = appState.cart[index];
    if (item.db_id) return; // No permitir editar items ya guardados en DB desde aquí

    const newQty = item.quantity + delta;
    
    if (newQty <= 0) {
        removeFromCart(itemId);
    } else {
        item.quantity = newQty;
        const modifierTotal = item.modifiers.reduce((acc: number, m: any) => acc + (m.extra_price || 0), 0);
        item.total_price = (item.base_price + modifierTotal) * item.quantity;
        appState.cart = [...appState.cart];
    }
    persistSession();
}

export function clearCart() {
    appState.cart = [];
    persistSession();
}

export function setActiveTable(table: any | null, order: any | null = null) {
    appState.activeTable = table;
    appState.activeOrder = order;
    if (!table && !order) {
        appState.activeOrder = null;
    }
    persistSession();
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
    persistSession();
}
