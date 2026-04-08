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
        })
};
