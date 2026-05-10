import { fetchApi } from '../api';
import type { OrderStatus } from './orders';

export interface KitchenTicket {
    id: number;
    order_id: number;
    item_id: number;
    product_name: string;
    variant_name: string | null;
    modifiers_text: string | null;
    status: 'PENDING' | 'PREPARING' | 'READY' | 'DELIVERED' | 'CANCELLED';
    received_at: string;
    started_at: string | null;
    finished_at: string | null;
}

export const KitchenService = {
    /** Obtiene todos los tickets activos (PENDING, PREPARING). */
    getActiveTickets: () => 
        fetchApi<KitchenTicket[]>('/api/v1/pos/kitchen/tickets'),

    /** Marca un ticket como 'En preparación'. */
    startPreparing: (ticketId: number, cookUuid: string, cookName: string) =>
        fetchApi<{status: string}>(`/api/v1/pos/kitchen/tickets/${ticketId}/prepare?cook_uuid=${cookUuid}&cook_name=${cookName}`, {
            method: 'POST'
        }),

    /** Marca un ítem como 'En preparación' (vía ID de ítem). */
    startPreparingItem: (itemId: number, cookUuid: string, cookName: string) =>
        fetchApi<{status: string}>(`/api/v1/pos/kitchen/items/${itemId}/prepare?cook_uuid=${cookUuid}&cook_name=${cookName}`, {
            method: 'POST'
        }),

    /** Marca un ticket como 'Listo'. */
    markAsReady: (ticketId: number) =>
        fetchApi<{status: string}>(`/api/v1/pos/kitchen/tickets/${ticketId}/ready`, {
            method: 'POST'
        }),

    /** Marca un ítem como 'Listo' (vía ID de ítem). */
    markItemAsReady: (itemId: number) =>
        fetchApi<{status: string}>(`/api/v1/pos/kitchen/items/${itemId}/ready`, {
            method: 'POST'
        })
};
