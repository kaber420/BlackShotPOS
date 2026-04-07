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
    getAll: () => fetchApi<Table[]>('/api/v1/pos/tables'),
    
    create: (number: number, capacity: number = 4, location?: string) => 
        fetchApi<Table>(`/api/v1/pos/tables?number=${number}&capacity=${capacity}${location ? `&location=${location}` : ''}`, {
            method: 'POST'
        }),

    updateStatus: (id: number, status: TableStatus) =>
        fetchApi<Table>(`/api/v1/pos/tables/${id}/status?status=${status}`, {
            method: 'PATCH'
        })
};
