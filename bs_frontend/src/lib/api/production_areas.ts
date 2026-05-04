import { fetchApi } from '../api';

export interface ProductionArea {
    id: number;
    name: string;
    description?: string;
    is_active: boolean;
}

export const ProductionAreaService = {
    getAll: () => fetchApi<ProductionArea[]>('/api/v1/pos/catalog/production/areas'),
    
    create: (area: Partial<ProductionArea>) =>
        fetchApi<ProductionArea>('/api/v1/pos/catalog/production/areas', {
            method: 'POST',
            body: JSON.stringify(area)
        }),

    update: (id: number, area: Partial<ProductionArea>) =>
        fetchApi<ProductionArea>(`/api/v1/pos/catalog/production/areas/${id}`, {
            method: 'PUT',
            body: JSON.stringify(area)
        }),

    delete: (id: number) =>
        fetchApi<{detail: string}>(`/api/v1/pos/catalog/production/areas/${id}`, {
            method: 'DELETE'
        })
};
