const BASE = '/api/v1/pos/customers';

function authHeaders() {
    return { 'Content-Type': 'application/json' };
}

export interface Customer {
    id: string;
    username: string;
    loyalty_code: string;
    nfc_tag_id?: string;
    points: number;
    credit_balance: number;
    tier: string;
    is_active: boolean;
    name?: string;
    phone?: string;
    email?: string;
    custom_metadata?: Record<string, any>;
    created_at?: string;
    last_visit_at?: string;
}

export interface CustomerCreatePayload {
    name: string;
    username: string;
    password?: string;
    phone?: string;
    email?: string;
}

export interface CustomerUpdatePayload {
    name?: string;
    phone?: string;
    email?: string;
    password?: string;
    points?: number;
    credit_balance?: number;
    tier?: string;
    nfc_tag_id?: string;
    custom_metadata?: Record<string, any>;
    is_active?: boolean;
}

export const CustomerService = {
    async list(limit = 50): Promise<Customer[]> {
        const res = await fetch(`${BASE}/?limit=${limit}`, {
            headers: authHeaders(),
            credentials: 'include'
        });
        if (!res.ok) throw new Error('Error al listar clientes');
        return res.json();
    },

    async search(query: string): Promise<Customer[]> {
        const res = await fetch(`${BASE}/search?q=${encodeURIComponent(query)}`, {
            headers: authHeaders(),
            credentials: 'include'
        });
        if (!res.ok) throw new Error('Error al buscar clientes');
        return res.json();
    },

    async get(id: string): Promise<Customer> {
        const res = await fetch(`${BASE}/${id}`, {
            headers: authHeaders(),
            credentials: 'include'
        });
        if (!res.ok) throw new Error('Cliente no encontrado');
        return res.json();
    },

    async create(payload: CustomerCreatePayload): Promise<Customer> {
        const res = await fetch(`${BASE}/`, {
            method: 'POST',
            headers: authHeaders(),
            credentials: 'include',
            body: JSON.stringify(payload)
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail ?? 'Error al crear el cliente');
        }
        return res.json();
    },

    async update(id: string, payload: CustomerUpdatePayload): Promise<Customer> {
        const res = await fetch(`${BASE}/${id}`, {
            method: 'PATCH',
            headers: authHeaders(),
            credentials: 'include',
            body: JSON.stringify(payload)
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail ?? 'Error al actualizar el cliente');
        }
        return res.json();
    }
};
