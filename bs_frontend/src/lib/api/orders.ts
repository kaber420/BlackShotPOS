import { fetchApi } from '../api';

// ---------------------------------------------------------------------------
// Enums — espejo de pos_core/sales/models.py
// ---------------------------------------------------------------------------

export enum OrderType {
    DINE_IN = "DINE_IN",
    TAKEAWAY = "TAKEAWAY",
    DELIVERY = "DELIVERY"
}

/** Estados operativos de una orden. PAID fue eliminado en Fase 3:
 *  el flag `is_paid: boolean` reemplaza ese estado. */
export enum OrderStatus {
    PENDING = "PENDING",
    PREPARING = "PREPARING",
    READY = "READY",
    DELIVERED = "DELIVERED",
    CANCELLED = "CANCELLED"
}

export enum PaymentMethod {
    CASH = "cash",
    CARD = "card",
    TRANSFER = "transfer",
    OTHER = "other"
}

// ---------------------------------------------------------------------------
// Sub-interfaces — espejo de pos_core/sales/schemas.py
// ---------------------------------------------------------------------------

export interface MeasureRead {
    id: number;
    name: string;
    value: number;
    unit: string;
}

export interface VariantRead {
    id: number;
    price: number;
    measure: MeasureRead | null;
}

export interface ProductSimpleRead {
    id: number;
    name: string;
    recipe_markdown: string | null;
}

export interface ModifierSimpleRead {
    id: number;
    name: string;
    extra_price: number;
}

export interface PaymentRead {
    id: number;
    method: PaymentMethod;
    amount: number;
    timestamp: string; // ISO 8601 UTC
}

// ---------------------------------------------------------------------------
// OrderItem — espejo 1:1 de OrderItemRead en schemas.py
// ---------------------------------------------------------------------------

export interface OrderItem {
    id: number;
    product_id: number;
    product_variant_id: number | null;
    quantity: number;
    unit_price: number;
    status: OrderStatus;

    // Relaciones anidadas
    product: ProductSimpleRead | null;
    variant: VariantRead | null;
    modifiers: ModifierSimpleRead[];

    // Rastreo de cocinero y mesero
    cook_uuid: string | null;
    cook_name: string | null;
    delivered_by_uuid: string | null;
    delivered_by_name: string | null;

    // Timestamps de ciclo de vida del ítem (ISO 8601 UTC)
    preparing_at: string | null;
    ready_at: string | null;
    delivered_at: string | null;
}

// ---------------------------------------------------------------------------
// Order — espejo 1:1 de OrderRead en schemas.py
// ---------------------------------------------------------------------------

export interface Order {
    id: number;
    type: OrderType;
    status: OrderStatus;
    /** true si el pago fue registrado. Reemplaza el antiguo estado PAID. */
    is_paid: boolean;
    table_id: number | null;
    shift_id: number | null;
    external_reference: string | null;
    created_at: string; // ISO 8601 UTC
    updated_at: string; // ISO 8601 UTC

    // Rastreo del mesero creador
    waiter_uuid: string | null;
    waiter_name: string | null;

    // Rastreo del cocinero responsable
    cook_uuid: string | null;
    cook_name: string | null;

    // Timestamps de ciclo de vida de la orden (ISO 8601 UTC)
    preparing_at: string | null;
    ready_at: string | null;
    delivered_at: string | null;

    // Relaciones anidadas
    items: OrderItem[];
    payments: PaymentRead[];
}

// ---------------------------------------------------------------------------
// OrderService — cliente HTTP
// ---------------------------------------------------------------------------

export const OrderService = {
    getAll: (status?: OrderStatus) => {
        const url = status ? `/api/v1/pos/orders?status=${status}` : '/api/v1/pos/orders';
        return fetchApi<Order[]>(url);
    },

    getById: (id: number) =>
        fetchApi<Order>(`/api/v1/pos/orders/${id}`),

    create: (order: { type: OrderType; table_id?: number; external_reference?: string }) =>
        fetchApi<Order>('/api/v1/pos/orders', {
            method: 'POST',
            body: JSON.stringify(order)
        }),

    addItem: (
        orderId: number,
        productId: number,
        quantity: number = 1,
        productVariantId?: number,
        modifierIds: number[] = []
    ) =>
        fetchApi<OrderItem>(`/api/v1/pos/orders/${orderId}/items`, {
            method: 'POST',
            body: JSON.stringify({
                product_id: productId,
                quantity,
                product_variant_id: productVariantId ?? null,
                modifier_ids: modifierIds
            })
        }),

    updateStatus: (orderId: number, status: OrderStatus) =>
        fetchApi<Order>(`/api/v1/pos/orders/${orderId}/status?status=${status}`, {
            method: 'PATCH'
        }),

    updateItemStatus: (orderId: number, itemId: number, status: OrderStatus) =>
        fetchApi<OrderItem>(`/api/v1/pos/orders/${orderId}/items/${itemId}/status?status=${status}`, {
            method: 'PATCH'
        }),

    pay: (orderId: number, method: PaymentMethod | string, amount: number, vacateTable: boolean = true) =>
        fetchApi<PaymentRead>(`/api/v1/pos/orders/${orderId}/payments`, {
            method: 'POST',
            body: JSON.stringify({ method, amount, vacate_table: vacateTable })
        }),

    delete: (orderId: number) =>
        fetchApi<{ status: string; message: string }>(`/api/v1/pos/orders/${orderId}`, {
            method: 'DELETE'
        }),

    cancelWithReason: (orderId: number, reason: string) =>
        fetchApi<{ status: string }>(`/api/v1/pos/audits/orders/${orderId}/cancel`, {
            method: 'POST',
            body: JSON.stringify({ reason })
        }),

    transfer: (orderId: number, newTableId: number) =>
        fetchApi<Order>(`/api/v1/pos/orders/${orderId}/transfer`, {
            method: 'POST',
            body: JSON.stringify({ new_table_id: newTableId })
        })
};

