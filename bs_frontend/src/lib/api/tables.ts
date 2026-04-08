import { fetchApi } from '../api';

export type TableStatus = 'Free' | 'Occupied' | 'Reserved' | 'Out of order';

export interface Table {
    id: number;
    number: number;
    capacity: number;
    status: TableStatus;
    location?: string;
    is_active: boolean;
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
        })
};
