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
    if (!table) {
        appState.activeOrder = null;
    }
}
