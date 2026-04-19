import { appState } from './app_state.svelte';

/**
 * Formatea un número como moneda usando la configuración global
 */
export function formatCurrency(amount: number | string): string {
    const value = typeof amount === 'string' ? parseFloat(amount) : amount;
    if (isNaN(value)) return '$0.00';
    
    return new Intl.NumberFormat(appState.settings.locale || 'es-MX', {
        style: 'currency',
        currency: appState.settings.currency_code || 'MXN',
        minimumFractionDigits: 2
    }).format(value);
}

/**
 * Formatea una fecha ISO a formato legible usando el locale global
 */
export function formatDate(dateStr: string | null): string {
    if (!dateStr) return '—';
    const date = new Date(dateStr);
    return date.toLocaleDateString(appState.settings.locale || 'es-MX', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
}

/**
 * Formatea una fecha ISO a formato con hora usando el locale global
 */
export function formatDateTime(dateStr: string | null): string {
    if (!dateStr) return '—';
    const date = new Date(dateStr);
    return date.toLocaleString(appState.settings.locale || 'es-MX', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}
