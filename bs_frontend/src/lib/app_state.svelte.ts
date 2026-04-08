import { page } from '$app/state';

export const appState = $state({
    currentTheme: 'corporate',
    isLoggedIn: false,
    cart: [] as any[],
    activeTable: null as any | null,
    activeOrder: null as any | null,
});

export function setTheme(theme: string) {
    appState.currentTheme = theme;
    if (typeof document !== 'undefined') {
        document.documentElement.setAttribute('data-theme', theme);
    }
}

export function setAuth(status: boolean) {
    appState.isLoggedIn = status;
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
                total_price: item.unit_price * item.quantity
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
