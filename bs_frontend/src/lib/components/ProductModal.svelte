<script lang="ts">
    import { ProductService, type Product, type Measure, type ProductVariant, type ModifierGroup, type Tax } from '$lib/api/products';
    import { IngredientService, type Ingredient } from '$lib/api/ingredients';
    import type { Category } from '$lib/api/categories';
    import { onMount } from 'svelte';
    import Button from './ui/Button.svelte';

    import ProductGeneralForm from './product/ProductGeneralForm.svelte';
    import ProductNutritionForm from './product/ProductNutritionForm.svelte';
    import ProductRecipeForm from './product/ProductRecipeForm.svelte';
    import ProductVariantsManager from './product/ProductVariantsManager.svelte';
    import ProductModifiersForm from './product/ProductModifiersForm.svelte';

    let { isOpen, product, categories, onClose, onSave } = $props<{
        isOpen: boolean;
        product: Partial<Product> | null;
        categories: Category[];
        onClose: () => void;
        onSave: () => void;
    }>();

    let activeTab = $state<'general' | 'recipe' | 'variants' | 'modifiers'>('general');
    let formData = $state<Partial<Product>>({
        name: '',
        description: '',
        price: 0,
        stock: 0,
        is_active: true,
        category_id: undefined,
        image_url: '',
        protein: 0,
        calories: 0,
        carbs: 0,
        fats: 0,
        recipe_markdown: ''
    });

    let availableMeasures = $state<Measure[]>([]);
    let availableIngredients = $state<Ingredient[]>([]);
    let availableModifierGroups = $state<ModifierGroup[]>([]);
    let availableTaxes = $state<Tax[]>([]);
    let selectedVariants = $state<(Partial<ProductVariant> & { recipe?: any[] })[]>([]);
    
    let modMeasureQuantities = $state<Record<string, number>>({});
    let deletedVariantIds = $state<number[]>([]);
    let isSaving = $state(false);
    let errorMessage = $state('');

    async function loadInitialData() {
        try {
            const [measures, ingredients, modGroups, taxes] = await Promise.all([
                ProductService.getMeasures(),
                IngredientService.getAll(),
                ProductService.getModifierGroups(),
                ProductService.getTaxes()
            ]);
            availableMeasures = measures;
            availableIngredients = ingredients;
            availableModifierGroups = modGroups;
            availableTaxes = taxes;
        } catch (e) {
            console.error(e);
        }
    }

    onMount(loadInitialData);

    let lastProductId = $state<number | undefined>(undefined);
    let isLoadingVariants = $state(false);

    $effect(() => {
        const currentId = product?.id;
        if (currentId !== lastProductId) {
            lastProductId = currentId;
            initializeLocalState();
        }
    });

    async function initializeLocalState() {
        if (product) {
            formData = { ...product };
            if (product.variants && product.variants.length > 0) {
                isLoadingVariants = true;
                await loadVariantRecipes(product.variants, product.id);
                isLoadingVariants = false;
            } else {
                selectedVariants = [];
            }
        } else {
            formData = {
                name: '',
                description: '',
                price: 0,
                stock: 0,
                is_active: true,
                category_id: categories.length > 0 ? categories[0].id : undefined,
                image_url: '',
                protein: 0,
                calories: 0,
                carbs: 0,
                fats: 0,
                recipe_markdown: ''
            };
            selectedVariants = [];
            deletedVariantIds = [];
        }
    }

    async function loadVariantRecipes(variants: ProductVariant[], targetProductId?: number) {
        const variantsWithRecipes = await Promise.all(variants.map(async v => {
            if (v.id) {
                const recipe = await ProductService.getVariantRecipe(v.id);
                return { ...v, recipe };
            }
            return { ...v, recipe: [] };
        }));
        
        if (targetProductId === product?.id) {
            selectedVariants = variantsWithRecipes;
        }
    }

    async function handleSave() {
        if (!formData.name) {
            errorMessage = 'El nombre es obligatorio.';
            return;
        }

        isUploading = false; // Reset just in case
        isSaving = true;
        errorMessage = '';
        try {
            let savedProduct: Product;
            if (product?.id) {
                savedProduct = await ProductService.update(product.id, formData);
            } else {
                savedProduct = await ProductService.create(formData);
            }

            // 1. Eliminar Variantes que fueron removidas en el UI
            if (deletedVariantIds.length > 0) {
                for (const vid of deletedVariantIds) {
                    await ProductService.deleteVariant(vid);
                }
                deletedVariantIds = [];
            }

            // 2. Vincular Grupos de Modificadores (Extras Disponibles) al producto
            if (formData.modifier_groups) {
                for (const group of formData.modifier_groups) {
                    if (group.id) await ProductService.linkModifierGroup(savedProduct.id!, group.id);
                }
            }

            // 3. Guardar/Actualizar Variantes y sus Recetas
            if (savedProduct.id && selectedVariants.length > 0) {
                for (const variant of selectedVariants) {
                    const variantData = { 
                        measure_id: variant.measure_id,
                        price: variant.price,
                        image_url: variant.image_url,
                        protein: variant.protein,
                        calories: variant.calories,
                        carbs: variant.carbs,
                        fats: variant.fats
                    };

                    let savedVariant: ProductVariant;
                    if (variant.id) {
                        savedVariant = await ProductService.updateVariant(variant.id, variantData);
                    } else {
                        savedVariant = await ProductService.createVariant(savedProduct.id, variantData);
                    }

                    // Guardar Receta de la Variante (borrar previa y re-crear es más robusto)
                    if (variant.recipe) {
                        if (variant.id) {
                            await ProductService.clearVariantRecipe(variant.id);
                        }
                        
                        for (const ri of variant.recipe) {
                            if (ri.input_quantity > 0 || ri.quantity > 0) {
                                if (ri.ingredient_id) {
                                    await ProductService.addIngredientToVariant(
                                        savedVariant.id!, 
                                        ri.ingredient_id, 
                                        ri.quantity,
                                        ri.input_quantity,
                                        ri.input_unit
                                    );
                                } else if (ri.modifier_group_id) {
                                    await ProductService.addModifierGroupToVariant(
                                        savedVariant.id!, 
                                        ri.modifier_group_id, 
                                        ri.quantity,
                                        ri.input_quantity,
                                        ri.input_unit
                                    );
                                }
                            }
                        }
                    }
                }
            }

            // 3. Guardar Cantidades de Modificadores por Medida (Configuraciones específicas de extras)
            for (const [key, qty] of Object.entries(modMeasureQuantities)) {
                if (qty === undefined || qty === null) continue;
                const [modId, measureId] = key.split('-').map(Number);
                await ProductService.updateModifierMeasureQuantity(modId, measureId, qty);
            }

            onSave();
            onClose();
        } catch (error) {
            console.error('Error saving product:', error);
            errorMessage = 'Error al guardar el producto. Inténtalo de nuevo.';
        } finally {
            isSaving = false;
        }
    }

    // --- Gestión de Imágenes ---
    let isUploading = $state(false);

    async function handleImageUpload(e: Event) {
        const file = (e.target as HTMLInputElement).files?.[0];
        if (!file) return;

        isUploading = true;
        try {
            const res = await ProductService.uploadImage(file);
            // Si ya teníamos una imagen local, el backend la borrará al hacer el update
            // O podemos borrarla nosotros si es un cambio "borrador"
            formData.image_url = res.url;
        } catch (error) {
            console.error('Error uploading image:', error);
            errorMessage = 'Error al subir la imagen.';
        } finally {
            isUploading = false;
        }
    }

    async function handleVariantImageUpload(vIndex: number, e: Event) {
        const file = (e.target as HTMLInputElement).files?.[0];
        if (!file) return;

        isUploading = true;
        try {
            const res = await ProductService.uploadImage(file);
            selectedVariants[vIndex].image_url = res.url;
        } catch (error) {
            console.error('Error uploading variant image:', error);
            errorMessage = 'Error al subir la imagen de la variante.';
        } finally {
            isUploading = false;
        }
    }

    async function removeImage() {
        // El borrado físico lo maneja el backend al actualizar o podemos llamar explícitamente
        // Para inmediatez, si es local, lo borramos
        if (formData.image_url?.startsWith('/uploads/')) {
            const filename = formData.image_url.split('/').pop();
            if (filename) await ProductService.deleteImage(filename).catch(console.error);
        }
        formData.image_url = '';
    }

    async function removeVariantImage(vIndex: number) {
        const v = selectedVariants[vIndex];
        if (v.image_url?.startsWith('/uploads/')) {
            const filename = v.image_url.split('/').pop();
            if (filename) await ProductService.deleteImage(filename).catch(console.error);
        }
        v.image_url = '';
    }

</script>

{#if isOpen}
    <div class="modal modal-open">
        <div class="modal-box max-w-4xl bg-base-100 rounded-3xl border border-base-300 shadow-2xl p-0 overflow-hidden">
            <!-- Header -->
            <div class="p-6 bg-base-200/50 border-b border-base-300 flex justify-between items-center">
                <h3 class="font-bold text-2xl flex items-center gap-3">
                    <span class="p-2 bg-primary/10 rounded-lg text-primary">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" /></svg>
                    </span>
                    {product?.id ? 'Editar Producto' : 'Nuevo Producto'}
                </h3>
                <div class="tabs tabs-boxed bg-transparent">
                    <button class="tab {activeTab === 'general' ? 'tab-active' : ''}" onclick={() => activeTab = 'general'}>General</button>
                    <button class="tab {activeTab === 'recipe' ? 'tab-active' : ''}" onclick={() => activeTab = 'recipe'}>Receta</button>
                    <button class="tab {activeTab === 'variants' ? 'tab-active' : ''}" onclick={() => activeTab = 'variants'}>Tallas</button>
                    <button class="tab {activeTab === 'modifiers' ? 'tab-active' : ''}" onclick={() => activeTab = 'modifiers'}>Extras</button>
                </div>
            </div>

            <div class="p-8 h-[65vh] overflow-y-auto">
                {#if errorMessage}
                    <div class="alert alert-error mb-6 shadow-sm">
                        <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current flex-shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                        <span>{errorMessage}</span>
                    </div>
                {/if}

                {#if activeTab === 'general'}
                    <ProductGeneralForm
                        bind:formData
                        {categories}
                        taxes={availableTaxes}
                        bind:isUploading
                        {handleImageUpload}
                        {removeImage}
                    />

                {:else if activeTab === 'recipe'}
                    <div class="space-y-6">
                        <ProductNutritionForm bind:formData />
                        <ProductRecipeForm bind:formData />
                    </div>

                {:else if activeTab === 'variants'}
                    <ProductVariantsManager
                        bind:selectedVariants
                        {availableMeasures}
                        {availableIngredients}
                        {availableModifierGroups}
                        {isLoadingVariants}
                        bind:deletedVariantIds
                        {formData}
                        {handleVariantImageUpload}
                        {removeVariantImage}
                    />

                {:else if activeTab === 'modifiers'}
                    <ProductModifiersForm
                        bind:formData
                        {availableModifierGroups}
                    />
                {/if}
            </div>
            <!-- Footer -->
            <div class="bg-base-200/50 p-6 border-t border-base-300 flex justify-end gap-3">
                <Button variant="ghost" class="font-bold" onclick={onClose}>Cancelar</Button>
                <Button variant="primary" size="md" class="px-10 gap-2 shadow-lg shadow-primary/20 rounded-xl font-black uppercase tracking-widest text-xs" onclick={handleSave} isLoading={isSaving}>
                    {product?.id ? 'Guardar Cambios' : 'Crear Producto'}
                </Button>
            </div>
        </div>
        <button class="modal-backdrop bg-black/60" onclick={onClose}></button>
    </div>
{/if}
