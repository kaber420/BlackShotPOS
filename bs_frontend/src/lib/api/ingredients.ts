import { fetchApi } from '../api';

export interface IngredientBatch {
	id: number;
	current_quantity: number;
	expiration_date?: string;
	arrival_date: string;
}

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
	category: string;
	category_id?: number;
	batches?: IngredientBatch[];
}

export interface IngredientPaginated {
	items: Ingredient[];
	total: number;
	page: number;
	pages: number;
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
	expiration_date?: string;
}

export interface InventoryCategory {
	id?: number;
	name: string;
	description?: string;
}

export const IngredientService = {
	getIngredients: (params?: { search?: string; category?: string; category_ids?: number[]; stock_status?: string; limit?: number; offset?: number }) => {
		const searchParams = new URLSearchParams();
		if (params?.search) searchParams.append('search', params.search);
		if (params?.category) searchParams.append('category', params.category);
		if (params?.stock_status) searchParams.append('stock_status', params.stock_status);
		
		if (params?.category_ids && params.category_ids.length > 0) {
			params.category_ids.forEach(id => searchParams.append('category_id', id.toString()));
		}
		if (params?.limit) searchParams.append('limit', params.limit.toString());
		if (params?.offset) searchParams.append('offset', params.offset.toString());
		
		const query = searchParams.toString();
		return fetchApi<IngredientPaginated>(`/api/v1/pos/inventory/ingredients${query ? `?${query}` : ''}`);
	},
	
	create: (ingredient: Ingredient) => 
		fetchApi<Ingredient>('/api/v1/pos/inventory/ingredients', {
			method: 'POST',
			body: JSON.stringify(ingredient)
		}),

	update: (id: number, ingredient: Partial<Ingredient>) =>
		fetchApi<Ingredient>(`/api/v1/pos/inventory/ingredients/${id}`, {
			method: 'PUT',
			body: JSON.stringify(ingredient)
		}),

	delete: (id: number) =>
		fetchApi<{detail: string}>(`/api/v1/pos/inventory/ingredients/${id}`, {
			method: 'DELETE'
		}),

	// --- Categorías ---
	getCategories: () => fetchApi<InventoryCategory[]>('/api/v1/pos/inventory/categories'),
	
	createCategory: (category: InventoryCategory) =>
		fetchApi<InventoryCategory>('/api/v1/pos/inventory/categories', {
			method: 'POST',
			body: JSON.stringify(category)
		}),

	deleteCategory: (id: number) =>
		fetchApi<{detail: string}>(`/api/v1/pos/inventory/categories/${id}`, {
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

	getAll: async () => {
		const res = await IngredientService.getIngredients({ limit: 1000 });
		return res.items;
	}
};
