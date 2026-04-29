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

export enum AdjustmentReason {
	// Salidas
	WASTE = "WASTE",
	EXPIRED = "EXPIRED",
	ERROR = "ERROR",
	THEFT = "THEFT",
	PERSONAL_CONSUMPTION = "PERSONAL_CONSUMPTION",
	// Entradas
	PURCHASE = "PURCHASE",
	RESTOCK = "RESTOCK",
	// Ajustes
	PHYSICAL_COUNT = "PHYSICAL_COUNT",
	CORRECTION = "CORRECTION"
}

export interface InventoryAdjustment {
	id?: number;
	ingredient_id: number;
	quantity: number;
	reason: AdjustmentReason;
	note?: string;
	actor_uuid?: string;
	actor_name?: string;
	timestamp?: string;
}

export interface InventoryAdjustmentCreate {
	ingredient_id: number;
	quantity: number;
	reason: AdjustmentReason;
	note?: string;
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

	getAdjustments: (ingredientId?: number, limit: number = 50) => {
		const query = ingredientId ? `?ingredient_id=${ingredientId}&limit=${limit}` : `?limit=${limit}`;
		return fetchApi<InventoryAdjustment[]>(`/api/v1/pos/inventory/adjustments${query}`);
	},

	registerAdjustment: (adjustment: InventoryAdjustmentCreate) =>
		fetchApi<InventoryAdjustment>('/api/v1/pos/inventory/adjustments', {
			method: 'POST',
			body: JSON.stringify(adjustment)
		}),
};
