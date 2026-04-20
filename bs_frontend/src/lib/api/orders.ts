import { fetchApi } from '../api';

export enum OrderType {
    DINE_IN = "DINE_IN",
    TAKEAWAY = "TAKEAWAY",
    DELIVERY = "DELIVERY"
}

export enum OrderStatus {
    PENDING = "PENDING",
    PREPARING = "PREPARING",
    READY = "READY",
    PAID = "PAID",
    DELIVERED = "DELIVERED",
    CANCELLED = "CANCELLED"
}

export interface OrderItem {
    id: number;
    order_id: number;
    product_id: number;
    product?: {
        name: string;
        image_url?: string;
    };
    modifiers?: {
        name: string;
    }[];
    quantity: number;
    unit_price: number;
    subtotal: number;
    status?: OrderStatus;
}

export interface Order {
    id: number;
    type: OrderType;
    status: OrderStatus;
    is_paid: boolean;
    table_id?: number;
    external_reference?: string;
    created_at: string;
    updated_at: string;
    items?: OrderItem[];
}

export const OrderService = {
    getAll: (status?: OrderStatus) => {
        const url = status ? `/api/v1/pos/orders?status=${status}` : '/api/v1/pos/orders';
        return fetchApi<Order[]>(url);
    },

    getById: (id: number) =>
        fetchApi<Order>(`/api/v1/pos/orders/${id}`),

    create: (order: { type: OrderType, table_id?: number, external_reference?: string }) =>
        fetchApi<Order>('/api/v1/pos/orders', {
            method: 'POST',
            body: JSON.stringify(order)
        }),

    addItem: (orderId: number, productId: number, quantity: number = 1) =>
        fetchApi<OrderItem>(`/api/v1/pos/orders/${orderId}/items`, {
            method: 'POST',
            body: JSON.stringify({ product_id: productId, quantity })
        }),

    updateStatus: (orderId: number, status: OrderStatus) =>
        fetchApi<Order>(`/api/v1/pos/orders/${orderId}/status?status=${status}`, {
            method: 'PATCH'
        }),

    updateItemStatus: (orderId: number, itemId: number, status: OrderStatus) =>
        fetchApi<OrderItem>(`/api/v1/pos/orders/${orderId}/items/${itemId}/status?status=${status}`, {
            method: 'PATCH'
        }),

    pay: (orderId: number, method: string, amount: number, vacateTable: boolean = true) =>
        fetchApi<any>(`/api/v1/pos/orders/${orderId}/payments`, {
            method: 'POST',
            body: JSON.stringify({ method, amount, vacate_table: vacateTable })
        }),

    delete: (orderId: number) =>
        fetchApi<any>(`/api/v1/pos/orders/${orderId}`, {
            method: 'DELETE'
        }),

    cancelWithReason: (orderId: number, reason: string) =>
        fetchApi<any>(`/api/v1/pos/audits/orders/${orderId}/cancel`, {
            method: 'POST',
            body: JSON.stringify({ reason })
        })
};
