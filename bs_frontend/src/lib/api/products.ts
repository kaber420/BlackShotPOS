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
    input_quantity?: number;
    input_unit?: string;
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

export interface Tax {
    id: number;
    name: string;
    rate: number;
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
    recipe_markdown?: string;
    variants?: ProductVariant[];
    modifier_groups?: ModifierGroup[];
    tax?: Tax;
    tax_id?: number | null;
}

export const ProductService = {
    getAll: (categoryId?: number, includeInactive: boolean = false) => {
        let url = '/api/v1/pos/catalog/products?';
        const params = new URLSearchParams();
        if (categoryId) params.append('category_id', categoryId.toString());
        if (includeInactive) params.append('include_inactive', 'true');
        url += params.toString();
        return fetchApi<Product[]>(url);
    },
    
    create: (product: Partial<Product>) => 
        fetchApi<Product>('/api/v1/pos/catalog/products', {
            method: 'POST',
            body: JSON.stringify(product)
        }),

    update: (id: number, product: Partial<Product>) =>
        fetchApi<Product>(`/api/v1/pos/catalog/products/${id}`, {
            method: 'PUT',
            body: JSON.stringify(product)
        }),

    delete: (id: number) =>
        fetchApi<{detail: string}>(`/api/v1/pos/catalog/products/${id}`, {
            method: 'DELETE'
        }),

    // Impuestos
    getTaxes: () => fetchApi<Tax[]>('/api/v1/pos/catalog/taxes'),
    createTax: (tax: Partial<Tax>) =>
        fetchApi<Tax>('/api/v1/pos/catalog/taxes', {
            method: 'POST',
            body: JSON.stringify(tax)
        }),
    updateTax: (id: number, tax: Partial<Tax>) =>
        fetchApi<Tax>(`/api/v1/pos/catalog/taxes/${id}`, {
            method: 'PUT',
            body: JSON.stringify(tax)
        }),
    deleteTax: (id: number) =>
        fetchApi<{detail: string}>(`/api/v1/pos/catalog/taxes/${id}`, {
            method: 'DELETE'
        }),

    // Medidas y Variantes
    getMeasures: () => fetchApi<Measure[]>('/api/v1/pos/catalog/measures'),
    createMeasure: (measure: Partial<Measure>) => 
        fetchApi<Measure>('/api/v1/pos/catalog/measures', {
            method: 'POST',
            body: JSON.stringify(measure)
        }),
    
    createVariant: (productId: number, variant: Partial<ProductVariant>) =>
        fetchApi<ProductVariant>(`/api/v1/pos/catalog/products/${productId}/variants`, {
            method: 'POST',
            body: JSON.stringify(variant)
        }),

    updateVariant: (variantId: number, variant: Partial<ProductVariant>) =>
        fetchApi<ProductVariant>(`/api/v1/pos/catalog/variants/${variantId}`, {
            method: 'PUT',
            body: JSON.stringify(variant)
        }),

    deleteVariant: (variantId: number) =>
        fetchApi<{detail: string}>(`/api/v1/pos/catalog/variants/${variantId}`, {
            method: 'DELETE'
        }),

    // Recetas (Ingredientes)
    getVariantRecipe: (variantId: number) => 
        fetchApi<any[]>(`/api/v1/pos/catalog/variants/${variantId}/recipe`),
    
    addIngredientToVariant: (variantId: number, ingredientId: number, quantity: number, input_quantity?: number, input_unit?: string) => {
        let url = `/api/v1/pos/catalog/variants/${variantId}/ingredients?ingredient_id=${ingredientId}&quantity=${quantity}`;
        if (input_quantity !== undefined) url += `&input_quantity=${input_quantity}`;
        if (input_unit) url += `&input_unit=${input_unit}`;
        return fetchApi<any>(url, { method: 'POST' });
    },

    addChildProductToProduct: (productId: number, childProductId: number, quantity: number = 1, childVariantId?: number) => {
        let url = `/api/v1/pos/catalog/products/${productId}/child-products?child_product_id=${childProductId}&quantity=${quantity}`;
        if (childVariantId) url += `&child_variant_id=${childVariantId}`;
        return fetchApi<any>(url, { method: 'POST' });
    },

    clearVariantRecipe: (variantId: number) =>
        fetchApi<{detail: string}>(`/api/v1/pos/catalog/variants/${variantId}/recipe`, {
            method: 'DELETE'
        }),

    addModifierGroupToVariant: (variantId: number, groupId: number, quantity: number, input_quantity?: number, input_unit?: string) => {
        let url = `/api/v1/pos/catalog/variants/${variantId}/modifier-groups?modifier_group_id=${groupId}&quantity=${quantity}`;
        if (input_quantity !== undefined) url += `&input_quantity=${input_quantity}`;
        if (input_unit) url += `&input_unit=${input_unit}`;
        return fetchApi<any>(url, { method: 'POST' });
    },

    // Modificadores
    getModifierGroups: () => fetchApi<ModifierGroup[]>('/api/v1/pos/catalog/modifier-groups'),
    
    createModifierGroup: (group: Partial<ModifierGroup>) =>
        fetchApi<ModifierGroup>('/api/v1/pos/catalog/modifier-groups', {
            method: 'POST',
            body: JSON.stringify(group)
        }),

    deleteModifierGroup: (id: number) =>
        fetchApi<{detail: string}>(`/api/v1/pos/catalog/modifier-groups/${id}`, {
            method: 'DELETE'
        }),

    createModifier: (modifier: Partial<Modifier>) =>
        fetchApi<Modifier>('/api/v1/pos/catalog/modifiers', {
            method: 'POST',
            body: JSON.stringify(modifier)
        }),

    deleteModifier: (id: number) =>
        fetchApi<{detail: string}>(`/api/v1/pos/catalog/modifiers/${id}`, {
            method: 'DELETE'
        }),

    linkModifierGroup: (productId: number, groupId: number) =>
        fetchApi<any>(`/api/v1/pos/catalog/products/${productId}/modifier-groups/${groupId}`, {
            method: 'POST'
        }),
    
    updateModifierMeasureQuantity: (modifierId: number, measure_id: number, quantity: number, input_quantity?: number, input_unit?: string) => {
        let url = `/api/v1/pos/catalog/modifiers/${modifierId}/measures/${measure_id}/quantity?quantity=${quantity}`;
        if (input_quantity !== undefined) url += `&input_quantity=${input_quantity}`;
        if (input_unit) url += `&input_unit=${input_unit}`;
        return fetchApi<any>(url, { method: 'POST' });
    },

    // Gestión de Imágenes
    uploadImage: (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        return fetchApi<{url: string, filename: string}>('/api/v1/pos/catalog/upload', {
            method: 'POST',
            body: formData
        });
    },

    deleteImage: (filename: string) =>
        fetchApi<{detail: string}>(`/api/v1/pos/catalog/upload/${filename}`, {
            method: 'DELETE'
        })
};
