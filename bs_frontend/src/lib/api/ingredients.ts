import { fetchApi } from '../api';

export interface Ingredient {
	id?: number;
	name: string;
	measure_type: 'weight' | 'volume' | 'unit';
	unit: string;
	current_stock: number;
	minimum_stock: number;
	protein_per_unit?: number;
	calories_per_unit?: number;
	carbs_per_unit?: number;
	fats_per_unit?: number;
}

export const IngredientService = {
	getAll: () => fetchApi<Ingredient[]>('/api/v1/pos/ingredients'),
	
	create: (ingredient: Ingredient) => 
		fetchApi<Ingredient>('/api/v1/pos/ingredients', {
			method: 'POST',
			body: JSON.stringify(ingredient)
		}),

	update: (id: number, ingredient: Partial<Ingredient>) =>
		fetchApi<Ingredient>(`/api/v1/pos/ingredients/${id}`, {
			method: 'PUT',
			body: JSON.stringify(ingredient)
		}),

	delete: (id: number) =>
		fetchApi<{detail: string}>(`/api/v1/pos/ingredients/${id}`, {
			method: 'DELETE'
		}),
};
