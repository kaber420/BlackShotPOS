import { fetchApi } from '../api';

export type TableStatus = 'Free' | 'Occupied' | 'Reserved' | 'Out of order';

export interface Table {
    id: number;
    number: number;
    capacity: number;
    status: TableStatus;
    location?: string;
    occupied_at?: string;
    is_active: boolean;
    waiter_requested?: boolean;
    bill_requested?: boolean;
}

export type ReservationStatus = 'PENDING' | 'CONFIRMED' | 'COMPLETED' | 'CANCELLED' | 'NO_SHOW';

export interface Reservation {
    id: number;
    customer_name: string;
    customer_phone?: string;
    customer_id?: string;
    table_id?: number;
    pax: number;
    reservation_time: string;
    status: ReservationStatus;
    notes?: string;
    created_at: string;
}

export const TableService = {
    getAll: (includeInactive: boolean = false) => {
        const url = includeInactive ? '/api/v1/pos/tables?include_inactive=true' : '/api/v1/pos/tables';
        return fetchApi<Table[]>(url);
    },
    
    create: (number: number, capacity: number = 4, location?: string) => 
    fetchApi<Table>(`/api/v1/pos/tables?number=${number}&capacity=${capacity}${location ? `&location=${location}` : ''}`, {
        method: 'POST'
    }),

    updateStatus: (id: number, status: TableStatus) =>
    fetchApi<Table>(`/api/v1/pos/tables/${id}/status?status=${status}`, {
        method: 'PATCH'
    }),

    vacate: (id: number) =>
    fetchApi<any>(`/api/v1/pos/tables/${id}/vacate`, {
        method: 'POST'
    }),

    update: (id: number, data: Partial<Table>) => {
        const params = new URLSearchParams();
        if (data.number !== undefined) params.append('number', data.number.toString());
        if (data.capacity !== undefined) params.append('capacity', data.capacity.toString());
        if (data.location !== undefined) params.append('location', data.location);
        if (data.is_active !== undefined) params.append('is_active', data.is_active.toString());
        
        return fetchApi<Table>(`/api/v1/pos/tables/${id}?${params.toString()}`, {
            method: 'PATCH'
        });
    },

    delete: (id: number) =>
        fetchApi<{detail: string}>(`/api/v1/pos/tables/${id}`, {
            method: 'DELETE'
        }),

    clearRequests: (id: number) =>
        fetchApi<Table>(`/api/v1/pos/tables/${id}/clear-requests`, {
            method: 'POST'
        })
};

export const ReservationService = {
    list: (startDate?: string, endDate?: string, status?: ReservationStatus) => {
        const params = new URLSearchParams();
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        if (status) params.append('status', status);
        return fetchApi<Reservation[]>(`/api/v1/pos/tables/reservations?${params.toString()}`);
    },

    create: (data: Partial<Reservation>) => 
        fetchApi<Reservation>('/api/v1/pos/tables/reservations', {
            method: 'POST',
            body: JSON.stringify(data)
        }),

    updateStatus: (id: number, status: ReservationStatus) =>
        fetchApi<Reservation>(`/api/v1/pos/tables/reservations/${id}/status?status=${status}`, {
            method: 'PATCH'
        }),

    checkIn: (id: number, waiterUuid?: string, waiterName?: string) => {
        const params = new URLSearchParams();
        if (waiterUuid) params.append('waiter_uuid', waiterUuid);
        if (waiterName) params.append('waiter_name', waiterName);
        return fetchApi<any>(`/api/v1/pos/tables/reservations/${id}/check-in?${params.toString()}`, {
            method: 'POST'
        });
    }
};
