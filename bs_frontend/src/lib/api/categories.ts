import { fetchApi } from '../api';

export interface Category {
	id?: number;
	name: string;
	description?: string;
	is_modifier_category: boolean;
}

export const CategoryService = {
	getAll: () => fetchApi<Category[]>('/api/v1/pos/catalog/categories'),
	
	create: (category: Partial<Category>) => 
		fetchApi<Category>('/api/v1/pos/catalog/categories', {
			method: 'POST',
			body: JSON.stringify(category)
		}),

	update: (id: number, category: Partial<Category>) =>
		fetchApi<Category>(`/api/v1/pos/catalog/categories/${id}`, {
			method: 'PUT',
			body: JSON.stringify(category)
		}),

	delete: (id: number) =>
		fetchApi<{detail: string}>(`/api/v1/pos/catalog/categories/${id}`, {
			method: 'DELETE'
		}),
};
