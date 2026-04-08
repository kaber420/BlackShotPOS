import { fetchApi } from '../api';

export interface Measure {
    id?: number;
    name: string;
    value: number;
    unit: string;
}

export interface ProductVariant {
    id?: number;
    product_id: number;
    measure_id: number;
    price: number;
    image_url?: string;
    protein?: number;
    calories?: number;
    carbs?: number;
    fats?: number;
    measure?: Measure;
}

export interface Modifier {
    id?: number;
    name: string;
    extra_price: number;
    ingredient_id?: number;
    quantity: number;
}

export interface ModifierGroup {
    id?: number;
    name: string;
    description?: string;
    min_selection: number;
    max_selection: number;
    is_required: boolean;
    modifiers: Modifier[];
}

export interface Product {
    id?: number;
    name: string;
    description?: string;
    price: number;
    image_url?: string;
    stock: number;
    is_active: boolean;
    category_id?: number;
    protein?: number;
    calories?: number;
    carbs?: number;
    fats?: number;
    variants?: ProductVariant[];
    modifier_groups?: ModifierGroup[];
}

export const ProductService = {
    getAll: (categoryId?: number) => {
        const url = categoryId ? `/api/v1/pos/products?category_id=${categoryId}` : '/api/v1/pos/products';
        return fetchApi<Product[]>(url);
    },
    
    create: (product: Partial<Product>) => 
        fetchApi<Product>('/api/v1/pos/products', {
            method: 'POST',
            body: JSON.stringify(product)
        }),

    update: (id: number, product: Partial<Product>) =>
        fetchApi<Product>(`/api/v1/pos/products/${id}`, {
            method: 'PUT',
            body: JSON.stringify(product)
        }),

    delete: (id: number) =>
        fetchApi<{detail: string}>(`/api/v1/pos/products/${id}`, {
            method: 'DELETE'
        }),

    // Medidas y Variantes
    getMeasures: () => fetchApi<Measure[]>('/api/v1/pos/measures'),
    createMeasure: (measure: Partial<Measure>) => 
        fetchApi<Measure>('/api/v1/pos/measures', {
            method: 'POST',
            body: JSON.stringify(measure)
        }),
    
    createVariant: (productId: number, variant: Partial<ProductVariant>) =>
        fetchApi<ProductVariant>(`/api/v1/pos/products/${productId}/variants`, {
            method: 'POST',
            body: JSON.stringify(variant)
        }),

    updateVariant: (variantId: number, variant: Partial<ProductVariant>) =>
        fetchApi<ProductVariant>(`/api/v1/pos/variants/${variantId}`, {
            method: 'PUT',
            body: JSON.stringify(variant)
        }),

    deleteVariant: (variantId: number) =>
        fetchApi<{detail: string}>(`/api/v1/pos/variants/${variantId}`, {
            method: 'DELETE'
        }),

    // Recetas (Ingredientes)
    getVariantRecipe: (variantId: number) => 
        fetchApi<any[]>(`/api/v1/pos/variants/${variantId}/recipe`),
    
    addIngredientToVariant: (variantId: number, ingredientId: number, quantity: number) =>
        fetchApi<any>(`/api/v1/pos/variants/${variantId}/ingredients?ingredient_id=${ingredientId}&quantity=${quantity}`, {
            method: 'POST'
        }),

    clearVariantRecipe: (variantId: number) =>
        fetchApi<{detail: string}>(`/api/v1/pos/variants/${variantId}/recipe`, {
            method: 'DELETE'
        }),

    addModifierGroupToVariant: (variantId: number, groupId: number, quantity: number) =>
        fetchApi<any>(`/api/v1/pos/variants/${variantId}/modifier-groups?modifier_group_id=${groupId}&quantity=${quantity}`, {
            method: 'POST'
        }),

    // Modificadores
    getModifierGroups: () => fetchApi<ModifierGroup[]>('/api/v1/pos/modifier-groups'),
    
    createModifierGroup: (group: Partial<ModifierGroup>) =>
        fetchApi<ModifierGroup>('/api/v1/pos/modifier-groups', {
            method: 'POST',
            body: JSON.stringify(group)
        }),

    deleteModifierGroup: (id: number) =>
        fetchApi<{detail: string}>(`/api/v1/pos/modifier-groups/${id}`, {
            method: 'DELETE'
        }),

    createModifier: (modifier: Partial<Modifier>) =>
        fetchApi<Modifier>('/api/v1/pos/modifiers', {
            method: 'POST',
            body: JSON.stringify(modifier)
        }),

    deleteModifier: (id: number) =>
        fetchApi<{detail: string}>(`/api/v1/pos/modifiers/${id}`, {
            method: 'DELETE'
        }),

    linkModifierGroup: (productId: number, groupId: number) =>
        fetchApi<any>(`/api/v1/pos/products/${productId}/modifier-groups/${groupId}`, {
            method: 'POST'
        }),
    
    updateModifierMeasureQuantity: (modifierId: number, measure_id: number, quantity: number) =>
        fetchApi<any>(`/api/v1/pos/modifiers/${modifierId}/measures/${measure_id}/quantity?quantity=${quantity}`, {
            method: 'POST'
        }),

    // Gestión de Imágenes
    uploadImage: (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        return fetchApi<{url: string, filename: string}>('/api/v1/pos/upload', {
            method: 'POST',
            body: formData
        });
    },

    deleteImage: (filename: string) =>
        fetchApi<{detail: string}>(`/api/v1/pos/upload/${filename}`, {
            method: 'DELETE'
        })
};
