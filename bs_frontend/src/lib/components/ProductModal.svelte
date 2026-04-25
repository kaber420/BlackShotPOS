<script lang="ts">
    import { ProductService, type Product, type Measure, type ProductVariant, type ModifierGroup } from '$lib/api/products';
    import { IngredientService, type Ingredient } from '$lib/api/ingredients';
    import type { Category } from '$lib/api/categories';
    import { onMount } from 'svelte';
    import Button from './ui/Button.svelte';

    let { isOpen, product, categories, onClose, onSave } = $props<{
        isOpen: boolean;
        product: Partial<Product> | null;
        categories: Category[];
        onClose: () => void;
        onSave: () => void;
    }>();

    let activeTab = $state<'general' | 'nutrition' | 'variants' | 'modifiers'>('general');
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
        fats: 0
    });

    let availableMeasures = $state<Measure[]>([]);
    let availableIngredients = $state<Ingredient[]>([]);
    let availableModifierGroups = $state<ModifierGroup[]>([]);
    let selectedVariants = $state<(Partial<ProductVariant> & { recipe?: any[] })[]>([]);
    
    // Unidades de medida restringidas por tipo
	const UNIT_OPTIONS = {
		weight: [
			{ id: 'g', name: 'Gramos (g)' },
			{ id: 'kg', name: 'Kilogramos (kg)' },
			{ id: 'oz', name: 'Onzas (oz)' },
			{ id: 'lb', name: 'Libras (lb)' }
		],
		volume: [
			{ id: 'ml', name: 'Mililitros (ml)' },
			{ id: 'L', name: 'Litros (L)' },
			{ id: 'fl_oz', name: 'Onzas Líquidas (fl oz)' }
		],
		unit: [
			{ id: 'pz', name: 'Piezas (pz)' },
			{ id: 'ud', name: 'Unidades' },
			{ id: 'porcion', name: 'Porción' }
		]
	};
    let modMeasureQuantities = $state<Record<string, number>>({});
    let deletedVariantIds = $state<number[]>([]);
    let isSaving = $state(false);
    let errorMessage = $state('');

    async function loadInitialData() {
        try {
            const [measures, ingredients, modGroups] = await Promise.all([
                ProductService.getMeasures(),
                IngredientService.getAll(),
                ProductService.getModifierGroups()
            ]);
            availableMeasures = measures;
            availableIngredients = ingredients;
            availableModifierGroups = modGroups;
        } catch (e) {
            console.error(e);
        }
    }

    onMount(loadInitialData);

    let lastProductId = $state<number | undefined>(undefined);
    let isLoadingVariants = $state(false);

    // Sincronizar formData cuando el producto cambia (solo si es un producto distinto)
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
                fats: 0
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
        
        // Solo actualizar si seguimos en el mismo producto (evitar race conditions)
        if (targetProductId === product?.id) {
            selectedVariants = variantsWithRecipes;
        }
    }

    function addVariant(measureId: number) {
        const measure = availableMeasures.find(m => m.id === measureId);
        if (!measure) return;
        
        // Evitar duplicados
        if (selectedVariants.some(v => v.measure_id === measureId)) return;

        selectedVariants = [...selectedVariants, {
            measure_id: measureId,
            measure: measure,
            price: formData.price || 0,
            image_url: '',
            protein: formData.protein || 0,
            calories: formData.calories || 0,
            carbs: formData.carbs || 0,
            fats: formData.fats || 0,
            recipe: []
        }];
    }

    function removeVariant(index: number) {
        const variant = selectedVariants[index];
        if (variant.id) {
            deletedVariantIds = [...deletedVariantIds, variant.id];
        }
        selectedVariants = selectedVariants.filter((_, i) => i !== index);
    }

    function addIngredientToVariant(vIndex: number) {
        if (!selectedVariants[vIndex].recipe) selectedVariants[vIndex].recipe = [];
        const firstIng = availableIngredients[0];
        selectedVariants[vIndex].recipe = [...selectedVariants[vIndex].recipe, { 
            ingredient_id: firstIng?.id, 
            quantity: 1,
            input_quantity: 1,
            input_unit: firstIng ? UNIT_OPTIONS[firstIng.measure_type][0].id : 'ml'
        }];
        selectedVariants = [...selectedVariants];
    }

    function addModifierGroupToVariantRecipe(vIndex: number) {
        if (!selectedVariants[vIndex].recipe) selectedVariants[vIndex].recipe = [];
        selectedVariants[vIndex].recipe = [...selectedVariants[vIndex].recipe, { 
            modifier_group_id: availableModifierGroups[0]?.id, 
            quantity: 1,
            input_quantity: 1,
            input_unit: 'ml'
        }];
        selectedVariants = [...selectedVariants];
    }

    function removeIngredientFromVariant(vIndex: number, rIndex: number) {
        selectedVariants[vIndex].recipe = selectedVariants[vIndex].recipe?.filter((_, i) => i !== rIndex);
        selectedVariants = [...selectedVariants];
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
        <div class="modal-box max-w-4xl bg-base-100 border border-base-300 shadow-2xl p-0 overflow-hidden">
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
                    <button class="tab {activeTab === 'nutrition' ? 'tab-active' : ''}" onclick={() => activeTab = 'nutrition'}>Nutrición</button>
                    <button class="tab {activeTab === 'variants' ? 'tab-active' : ''}" onclick={() => activeTab = 'variants'}>Tallas</button>
                    <button class="tab {activeTab === 'modifiers' ? 'tab-active' : ''}" onclick={() => activeTab = 'modifiers'}>Extras</button>
                </div>
            </div>

            <div class="p-8 max-h-[70vh] overflow-y-auto">
                {#if errorMessage}
                    <div class="alert alert-error mb-6 shadow-sm">
                        <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current flex-shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                        <span>{errorMessage}</span>
                    </div>
                {/if}

                {#if activeTab === 'general'}
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-8 animate-in fade-in slide-in-from-bottom-2">
                        <div class="flex flex-col gap-6">
                            <div class="form-control">
                                <label class="label font-bold text-xs uppercase tracking-widest opacity-60">Nombre</label>
                                <input type="text" placeholder="Ej: Café Americano" class="input input-bordered w-full focus:input-primary" bind:value={formData.name} />
                            </div>
                            <div class="form-control">
                                <label class="label font-bold text-xs uppercase tracking-widest opacity-60">Categoría</label>
                                <select class="select select-bordered w-full focus:select-primary" bind:value={formData.category_id}>
                                    <option disabled selected value={undefined}>Selecciona una categoría</option>
                                    {#each categories as category}
                                        <option value={category.id}>{category.name}</option>
                                    {/each}
                                </select>
                            </div>
                            <div class="grid grid-cols-2 gap-4">
                                <div class="form-control">
                                    <label class="label font-bold text-xs uppercase tracking-widest opacity-60">Precio (Sin Tallas) ($)</label>
                                    <input type="number" step="0.01" class="input input-bordered w-full focus:input-primary" bind:value={formData.price} />
                                    <span class="text-[9px] opacity-40 mt-1 uppercase">Se ignora si añades tallas específicas.</span>
                                </div>
                                <div class="form-control">
                                    <label class="label font-bold text-xs uppercase tracking-widest opacity-60">Stock Inicial</label>
                                    <input type="number" class="input input-bordered w-full focus:input-primary" bind:value={formData.stock} />
                                </div>
                            </div>
                        </div>
                        <div class="flex flex-col gap-6">
                            <div class="form-control">
                                <label class="label font-bold text-xs uppercase tracking-widest opacity-60">Foto del Producto</label>
                                <div class="flex flex-col gap-3">
                                    {#if formData.image_url}
                                        <div class="relative group w-full aspect-video rounded-2xl overflow-hidden border border-base-300 bg-base-200">
                                            <img src={formData.image_url} alt={formData.name} class="w-full h-full object-cover" />
                                            <div class="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                                                <Button variant="ghost" danger circle size="sm" onclick={removeImage} title="Eliminar Imagen">
                                                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                                                </Button>
                                                <label class="w-10 h-10 bg-primary text-white rounded-full flex items-center justify-center cursor-pointer shadow-lg hover:shadow-primary/40 hover:-translate-y-0.5 transition-all duration-200" title="Cambiar Imagen">
                                                    <input type="file" class="hidden" accept="image/*" onchange={handleImageUpload} />
                                                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a2 2 0 002 2h12a2 2 0 002-2v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
                                                </label>
                                            </div>
                                        </div>
                                    {:else}
                                        <label class="flex flex-col items-center justify-center w-full h-40 border-2 border-dashed border-base-300 rounded-2xl cursor-pointer hover:bg-base-200 transition-all gap-2 group">
                                            <input type="file" class="hidden" accept="image/*" onchange={handleImageUpload} />
                                            {#if isUploading}
                                                <span class="loading loading-spinner text-primary"></span>
                                            {:else}
                                                <svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10 opacity-20 group-hover:opacity-40 transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                                                <span class="text-[10px] font-black uppercase tracking-widest opacity-40">Subir Imagen</span>
                                            {/if}
                                        </label>
                                    {/if}
                                    <input type="text" placeholder="O pega una URL externa..." class="input input-bordered input-xs w-full focus:input-primary text-[10px]" bind:value={formData.image_url} />
                                </div>
                            </div>
                            <div class="form-control">
                                <label class="label font-bold text-xs uppercase tracking-widest opacity-60">Descripción</label>
                                <textarea class="textarea textarea-bordered h-28 focus:textarea-primary" placeholder="Descripción del producto..." bind:value={formData.description}></textarea>
                            </div>
                            <label class="label cursor-pointer justify-start gap-4">
                                <span class="label-text font-bold">¿Producto Activo?</span>
                                <input type="checkbox" class="toggle toggle-primary" bind:checked={formData.is_active} />
                            </label>
                        </div>
                    </div>

                {:else if activeTab === 'nutrition'}
                    <div class="bg-base-200/30 p-8 rounded-2xl border border-base-300 animate-in fade-in zoom-in-95">
                        <h4 class="text-xl font-bold mb-6 flex items-center gap-2">
                             Estimaciones Nutricionales (Por Porción Base)
                        </h4>
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-6">
                            <div class="form-control">
                                <label class="label font-bold text-xs uppercase opacity-60 text-primary">Proteína (g)</label>
                                <input type="number" class="input input-bordered text-center font-mono text-lg" bind:value={formData.protein} />
                            </div>
                            <div class="form-control">
                                <label class="label font-bold text-xs uppercase opacity-60 text-orange-500">Calorías (kcal)</label>
                                <input type="number" class="input input-bordered text-center font-mono text-lg" bind:value={formData.calories} />
                            </div>
                            <div class="form-control">
                                <label class="label font-bold text-xs uppercase opacity-60 text-blue-500">Carbos (g)</label>
                                <input type="number" class="input input-bordered text-center font-mono text-lg" bind:value={formData.carbs} />
                            </div>
                            <div class="form-control">
                                <label class="label font-bold text-xs uppercase opacity-60 text-emerald-500">Grasas (g)</label>
                                <input type="number" class="input input-bordered text-center font-mono text-lg" bind:value={formData.fats} />
                            </div>
                        </div>
                        <p class="mt-6 text-sm opacity-50 italic">
                            * Estos valores se usarán como referencia general. Puedes sobreescribirlos por tamaño en la sección "Tallas".
                        </p>
                    </div>

                {:else if activeTab === 'variants'}
                    <div class="flex flex-col gap-6 animate-in fade-in slide-in-from-right-4">
                        <div class="flex items-center gap-4 bg-primary/5 p-4 rounded-xl border border-primary/10">
                            <span class="text-sm font-bold opacity-70">Añadir Talla:</span>
                            <div class="flex flex-wrap gap-2">
                                {#each availableMeasures as m}
                                    <Button 
                                        variant="outline"
                                        size="sm"
                                        onclick={() => addVariant(m.id!)}
                                        disabled={selectedVariants.some(v => v.measure_id === m.id)}
                                        class={selectedVariants.some(v => v.measure_id === m.id) ? 'opacity-30' : ''}
                                    >
                                        + {m.name}
                                    </Button>
                                {/each}
                                {#if availableMeasures.length === 0}
                                    <span class="text-[10px] opacity-40 italic">Cargando medidas...</span>
                                {/if}
                            </div>
                        </div>

                        {#if isLoadingVariants}
                            <div class="py-20 text-center">
                                <span class="loading loading-spinner loading-lg text-primary"></span>
                                <p class="text-xs mt-2 opacity-50 uppercase font-black tracking-widest">Sincronizando recetas...</p>
                            </div>
                        {:else if selectedVariants.length === 0}
                            <div class="py-12 text-center opacity-30 border-2 border-dashed border-base-300 rounded-2xl">
                                <p class="text-lg">No has añadido tamaños para este producto.</p>
                                <p class="text-xs">Usa los botones de arriba para añadir variaciones como Chico, Mediano, etc.</p>
                            </div>
                        {:else}
                            <div class="flex flex-col gap-8">
                                {#each selectedVariants as variant, i}
                                    <div class="card bg-base-200/50 border border-base-300 p-6 flex flex-col gap-6 relative overflow-hidden">
                                        <div class="absolute top-0 left-0 w-1 h-full bg-primary"></div>
                                        <div class="flex justify-between items-center">
                                            <h5 class="font-black text-xl text-primary uppercase tracking-tighter">{variant.measure?.name}</h5>
                                            <Button variant="ghost" size="sm" danger onclick={() => removeVariant(i)}>Eliminar Talla</Button>
                                        </div>
                                                            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 items-end">
                                            <div class="form-control">
                                                <label class="label font-bold text-[10px] uppercase opacity-50" for="v-price-{i}">Precio Final ($)</label>
                                                <input id="v-price-{i}" type="number" step="0.01" class="input input-bordered input-sm font-bold border-primary/30" bind:value={variant.price} />
                                            </div>
                                            <div class="form-control md:col-span-2">
                                                <label class="label font-bold text-[10px] uppercase opacity-50">Imagen de la Talla (Opcional)</label>
                                                <div class="flex gap-3">
                                                    {#if variant.image_url}
                                                        <div class="relative group w-12 h-12 rounded-lg overflow-hidden border border-base-300">
                                                            <img src={variant.image_url} alt={variant.measure?.name} class="w-full h-full object-cover" />
                                                            <Button variant="ghost" size="xs" danger circle class="absolute inset-0 bg-error/80 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-white" onclick={() => removeVariantImage(i)}>
                                                                <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                                                            </Button>
                                                        </div>
                                                    {/if}
                                                    <div class="flex-1 flex flex-col gap-1">
                                                        <div class="flex gap-1">
                                                            <input type="text" class="input input-bordered input-xs flex-1 text-[10px]" bind:value={variant.image_url} placeholder="URL externa o selecciona archivo..." />
                                                            <label class="w-6 h-6 bg-primary text-white rounded flex items-center justify-center cursor-pointer shadow-sm hover:bg-primary/90 transition-all">
                                                                <input type="file" class="hidden" accept="image/*" onchange={(e) => handleVariantImageUpload(i, e)} />
                                                                <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a2 2 0 002 2h12a2 2 0 002-2v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
                                                            </label>
                                                        </div>
                                                        <span class="text-[9px] opacity-40 uppercase">Si está vacío usará la foto general.</span>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>

                                        <!-- Receta por Variante -->
                                        <div class="bg-base-100/50 p-4 rounded-xl border border-base-300">
                                            <div class="flex justify-between items-center mb-4">
                                                <h6 class="text-xs font-bold uppercase tracking-widest opacity-60 flex items-center gap-2">
                                                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>
                                                    Receta del Tamaño
                                                </h6>
                                                <div class="flex gap-2">
                                                    <Button variant="outline" size="xs" onclick={() => addIngredientToVariant(i)}>+ Fijo</Button>
                                                    <Button variant="outline" size="xs" onclick={() => addModifierGroupToVariantRecipe(i)}>+ Opcional</Button>
                                                </div>
                                            </div>

                                            {#if !variant.recipe || variant.recipe.length === 0}
                                                <p class="text-[10px] opacity-40 italic text-center py-4">No hay componentes en la receta.</p>
                                            {:else}
                                                <div class="flex flex-col gap-2">
                                                    {#each variant.recipe as ri, riIndex}
                                                        <div class="flex gap-2 items-end">
                                                            <div class="form-control flex-1">
                                                                <label class="label p-0 mb-1" for="v-{i}-ri-{riIndex}">
                                                                    <span class="label-text text-[9px] uppercase font-bold opacity-50">
                                                                        {ri.ingredient_id ? 'Ingrediente Fijo' : 'Elección de Grupo'}
                                                                    </span>
                                                                </label>
                                                                {#if ri.ingredient_id}
                                                                    <select id="v-{i}-ri-{riIndex}" class="select select-bordered select-xs w-full font-bold" bind:value={ri.ingredient_id}>
                                                                        {#each availableIngredients as ing}
                                                                            <option value={ing.id}>{ing.name} ({ing.unit})</option>
                                                                        {/each}
                                                                    </select>
                                                                {:else}
                                                                    <select id="v-{i}-ri-{riIndex}" class="select select-bordered select-secondary select-xs w-full font-bold" bind:value={ri.modifier_group_id}>
                                                                        <option value={undefined}>Selecciona un grupo...</option>
                                                                        {#each availableModifierGroups as group}
                                                                            <option value={group.id}>{group.name} (Grupo)</option>
                                                                        {/each}
                                                                    </select>
                                                                {/if}
                                                            </div>
                                                            <div class="form-control w-24">
                                                                <label class="label p-0 mb-1" for="v-{i}-ri-{riIndex}-qty">
                                                                    <span class="label-text text-[9px] uppercase font-bold opacity-50 text-center w-full">Cantidad</span>
                                                                </label>
                                                                <input id="v-{i}-ri-{riIndex}-qty" type="number" step="0.001" class="input input-bordered input-xs text-center font-bold" bind:value={ri.input_quantity} />
                                                            </div>
                                                            <div class="form-control w-20">
                                                                <label class="label p-0 mb-1">
                                                                    <span class="label-text text-[9px] uppercase font-bold opacity-50 text-center w-full">Unidad</span>
                                                                </label>
                                                                <select class="select select-bordered select-xs w-full font-bold" bind:value={ri.input_unit}>
                                                                    {#if ri.ingredient_id && availableIngredients.find(ingr => ingr.id === ri.ingredient_id)}
                                                                        {#each UNIT_OPTIONS[availableIngredients.find(ingr => ingr.id === ri.ingredient_id).measure_type] as u}
                                                                            <option value={u.id}>{u.id}</option>
                                                                        {/each}
                                                                    {:else}
                                                                        <option value="ml">ml</option>
                                                                        <option value="L">L</option>
                                                                        <option value="g">g</option>
                                                                        <option value="kg">kg</option>
                                                                    {/if}
                                                                </select>
                                                            </div>
                                                            <Button variant="ghost" size="sm" danger square onclick={() => removeIngredientFromVariant(i, riIndex)} title="Eliminar Componente">✕</Button>
                                                        </div>
                                                    {/each}
                                                </div>
                                            {/if}
                                        </div>

                                        <div class="grid grid-cols-4 gap-2 mt-4 pt-4 border-t border-base-300/30">
                                            <div class="form-control">
                                                <label class="label font-bold text-[9px] uppercase opacity-40 text-primary" for="v-prot-{i}">Proteína</label>
                                                <input id="v-prot-{i}" type="number" class="input input-ghost input-bordered input-xs text-center" bind:value={variant.protein} />
                                            </div>
                                            <div class="form-control">
                                                <label class="label font-bold text-[9px] uppercase opacity-40 text-orange-500" for="v-cal-{i}">Calorías</label>
                                                <input id="v-cal-{i}" type="number" class="input input-ghost input-bordered input-xs text-center" bind:value={variant.calories} />
                                            </div>
                                            <div class="form-control">
                                                <label class="label font-bold text-[9px] uppercase opacity-40 text-blue-500" for="v-carb-{i}">Carbos</label>
                                                <input id="v-carb-{i}" type="number" class="input input-ghost input-bordered input-xs text-center" bind:value={variant.carbs} />
                                            </div>
                                            <div class="form-control">
                                                <label class="label font-bold text-[9px] uppercase opacity-40 text-emerald-500" for="v-fat-{i}">Grasas</label>
                                                <input id="v-fat-{i}" type="number" class="input input-ghost input-bordered input-xs text-center" bind:value={variant.fats} />
                                            </div>
                                        </div>
                                    </div>
                                {/each}
                            </div>
                        {/if}
                    </div>

                {:else if activeTab === 'modifiers'}
                    <div class="flex flex-col gap-6 animate-in fade-in slide-in-from-right-4">
                        <div class="flex flex-col gap-4 bg-base-200/50 p-6 rounded-2xl border border-base-300">
                            <h4 class="font-bold text-sm uppercase tracking-widest opacity-60">Vincular Grupos de Extras</h4>
                            <div class="flex flex-wrap gap-2">
                                {#each availableModifierGroups as group}
                                    {@const isLinked = formData.modifier_groups?.some(g => g.id === group.id)}
                                    <Button 
                                        variant={isLinked ? 'primary' : 'outline'}
                                        size="sm"
                                        class={isLinked ? 'shadow-lg shadow-primary/20' : 'border-base-300'}
                                        onclick={() => {
                                            if (isLinked) {
                                                formData.modifier_groups = formData.modifier_groups?.filter(g => g.id !== group.id);
                                            } else {
                                                formData.modifier_groups = [...(formData.modifier_groups || []), group];
                                            }
                                        }}
                                    >
                                        {isLinked ? '✓' : '+'} {group.name}
                                    </Button>
                                {/each}
                                {#if availableModifierGroups.length === 0}
                                    <div class="alert alert-warning text-xs py-2 rounded-xl">
                                        No hay grupos creados. Ve a Inventario para crear grupos como "Leches".
                                    </div>
                                {/if}
                            </div>
                        </div>

                        {#if !formData.modifier_groups || formData.modifier_groups.length === 0}
                            <div class="py-12 text-center opacity-30 italic">
                                <p>No hay grupos de extras vinculados.</p>
                                <p class="text-xs">Selecciona arriba qué opciones (Leches, Jarabes, etc.) aplican a este producto.</p>
                            </div>
                        {:else}
                            <div class="flex flex-col gap-4">
                                {#each formData.modifier_groups as group}
                                    <div class="bg-base-100 p-6 rounded-2xl border border-base-200 shadow-sm">
                                        <div class="flex justify-between items-center mb-4">
                                            <h5 class="font-black text-lg tracking-tight text-primary flex items-center gap-2">
                                                <div class="w-1 h-5 bg-primary rounded-full"></div>
                                                {group.name}
                                            </h5>
                                            <span class="text-[10px] uppercase font-bold opacity-40 bg-base-200 px-3 py-1 rounded-full">
                                                {group.modifiers?.length || 0} opciones
                                            </span>
                                        </div>
                                        
                                        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                                            {#each group.modifiers || [] as mod}
                                                <div class="bg-base-200/30 p-3 rounded-xl border border-base-300/50 flex justify-between items-center">
                                                    <span class="text-sm font-bold opacity-80">{mod.name}</span>
                                                    <div class="flex items-center gap-2">
                                                        {#if mod.extra_price > 0}
                                                            <span class="badge badge-sm badge-outline font-bold text-[10px] opacity-60">+${mod.extra_price}</span>
                                                        {/if}
                                                    </div>
                                                </div>
                                            {/each}
                                        </div>
                                    </div>
                                {/each}
                            </div>
                        {/if}
                    </div>
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
