<script lang="ts">
    import type { Product, ProductVariant, Measure, ModifierGroup } from '$lib/api/products';
    import type { Ingredient } from '$lib/api/ingredients';
    import Button from '../ui/Button.svelte';

    let { 
        selectedVariants = $bindable(), 
        availableMeasures, 
        availableIngredients, 
        availableModifierGroups, 
        isLoadingVariants,
        deletedVariantIds = $bindable(),
        formData,
        handleVariantImageUpload,
        removeVariantImage
    } = $props<{
        selectedVariants: (Partial<ProductVariant> & { recipe?: any[] })[];
        availableMeasures: Measure[];
        availableIngredients: Ingredient[];
        availableModifierGroups: ModifierGroup[];
        isLoadingVariants: boolean;
        deletedVariantIds: number[];
        formData: Partial<Product>;
        handleVariantImageUpload: (index: number, e: Event) => void;
        removeVariantImage: (index: number) => void;
    }>();

    const UNIT_OPTIONS: Record<string, {id: string, name: string}[]> = {
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
            input_unit: firstIng ? firstIng.unit : 'ml'
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
</script>

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
                                                <select 
                                                    id="v-{i}-ri-{riIndex}" 
                                                    class="select select-bordered select-xs w-full font-bold" 
                                                    bind:value={ri.ingredient_id}
                                                    onchange={() => {
                                                        const ing = availableIngredients.find(ingr => ingr.id === ri.ingredient_id);
                                                        if (ing) ri.input_unit = ing.unit;
                                                    }}
                                                >
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
                                                    {#each UNIT_OPTIONS[availableIngredients.find(ingr => ingr.id === ri.ingredient_id)?.measure_type || 'volume'] || UNIT_OPTIONS['volume'] as u}
                                                        <option value={u.id}>{u.name}</option>
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
