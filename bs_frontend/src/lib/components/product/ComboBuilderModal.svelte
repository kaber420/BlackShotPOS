<script lang="ts">
    import { onMount } from 'svelte';
    import { ProductService, type Product } from '$lib/api/products';
    import { CategoryService, type Category } from '$lib/api/categories';
    import Button from '$lib/components/ui/Button.svelte';

    let { isOpen, onClose, onSave } = $props<{
        isOpen: boolean;
        onClose: () => void;
        onSave: () => void;
    }>();

    let products = $state<Product[]>([]);
    let categories = $state<Category[]>([]);
    let searchQuery = $state('');
    let isLoading = $state(false);

    // Combo Data
    let comboName = $state('');
    let comboPrice = $state<number>(0);
    let comboDescription = $state('');
    let comboImageUrl = $state('');
    let selectedItems = $state<{product: Product, quantity: number}[]>([]);

    let filteredProducts = $derived(
        products.filter(p => 
            p.name.toLowerCase().includes(searchQuery.toLowerCase()) && 
            p.is_active
        )
    );

    async function loadInitialData() {
        try {
            isLoading = true;
            const [p, c] = await Promise.all([
                ProductService.getAll(undefined, false),
                CategoryService.getAll()
            ]);
            products = p;
            categories = c;
        } catch (e) {
            console.error('Error loading data for combo builder:', e);
        } finally {
            isLoading = false;
        }
    }

    function addItem(product: Product) {
        const existing = selectedItems.find(item => item.product.id === product.id);
        if (existing) {
            existing.quantity += 1;
        } else {
            selectedItems.push({ product, quantity: 1 });
        }
    }

    function removeItem(productId: number) {
        selectedItems = selectedItems.filter(item => item.product.id !== productId);
    }

    function updateQuantity(productId: number, delta: number) {
        const item = selectedItems.find(i => i.product.id === productId);
        if (item) {
            item.quantity = Math.max(1, item.quantity + delta);
        }
    }

    async function handleSave() {
        if (!comboName || comboPrice <= 0 || selectedItems.length === 0) {
            alert('Por favor completa el nombre, precio y selecciona al menos un producto.');
            return;
        }

        try {
            isLoading = true;

            // 1. Asegurar categoría "Combos"
            let comboCategory = categories.find(c => c.name.toLowerCase() === 'combos');
            if (!comboCategory) {
                comboCategory = await CategoryService.create({
                    name: 'Combos',
                    description: 'Categoría generada automáticamente para paquetes y promociones.',
                    is_modifier_category: false
                });
            }

            // 2. Crear el Producto Combo
            const newCombo = await ProductService.create({
                name: comboName,
                description: comboDescription,
                price: comboPrice,
                image_url: comboImageUrl,
                category_id: comboCategory.id,
                is_active: true,
                stock: 0
            });

            // 3. Vincular productos hijos
            for (const item of selectedItems) {
                if (newCombo.id && item.product.id) {
                    await ProductService.addChildProductToProduct(
                        newCombo.id,
                        item.product.id,
                        item.quantity
                    );
                }
            }

            onSave();
            resetForm();
            onClose();
        } catch (e: any) {
            alert('Error al guardar el combo: ' + e.message);
        } finally {
            isLoading = false;
        }
    }

    function resetForm() {
        comboName = '';
        comboPrice = 0;
        comboDescription = '';
        comboImageUrl = '';
        selectedItems = [];
        searchQuery = '';
    }

    onMount(() => {
        loadInitialData();
    });
</script>

{#if isOpen}
    <div class="modal modal-open backdrop-blur-sm">
        <div class="modal-box max-w-5xl h-[90vh] flex flex-col p-0 overflow-hidden rounded-3xl border border-base-200 shadow-2xl">
            <!-- Header -->
            <div class="p-6 bg-base-100 border-b border-base-200 flex justify-between items-center">
                <div>
                    <h2 class="text-2xl font-black uppercase tracking-tight text-primary">Armar Nuevo Combo</h2>
                    <p class="text-xs opacity-60 font-bold uppercase tracking-widest">Crea paquetes con tus productos existentes</p>
                </div>
                <button class="btn btn-circle btn-ghost" onclick={onClose}>
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>

            <div class="flex-1 flex overflow-hidden">
                <!-- Left Column: Search & Selection -->
                <div class="w-1/2 p-6 border-r border-base-200 flex flex-col gap-4 bg-base-200/30">
                    <div class="form-control">
                        <div class="relative w-full">
                            <input 
                                type="text" 
                                placeholder="Buscar productos para el combo..." 
                                class="input input-bordered w-full pl-10 bg-base-100" 
                                bind:value={searchQuery}
                            />
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 absolute left-3 top-3.5 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                            </svg>
                        </div>
                    </div>

                    <div class="flex-1 overflow-y-auto pr-2 flex flex-col gap-2">
                        {#each filteredProducts as prod}
                            <button 
                                class="flex items-center gap-4 p-3 bg-base-100 hover:bg-primary/5 rounded-2xl border border-base-200 transition-all group text-left"
                                onclick={() => addItem(prod)}
                            >
                                <div class="w-12 h-12 rounded-xl bg-base-200 overflow-hidden flex-shrink-0">
                                    {#if prod.image_url}
                                        <img src={prod.image_url} alt={prod.name} class="w-full h-full object-cover" />
                                    {:else}
                                        <div class="w-full h-full flex items-center justify-center opacity-20">
                                            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                                        </div>
                                    {/if}
                                </div>
                                <div class="flex-1">
                                    <p class="font-bold text-sm line-clamp-1">{prod.name}</p>
                                    <p class="text-[10px] opacity-50 uppercase font-black">${prod.price.toFixed(2)}</p>
                                </div>
                                <div class="opacity-0 group-hover:opacity-100 transition-opacity">
                                    <span class="badge badge-primary font-bold">+Añadir</span>
                                </div>
                            </button>
                        {/each}
                    </div>
                </div>

                <!-- Right Column: Combo Details & List -->
                <div class="w-1/2 p-6 flex flex-col gap-6 bg-base-100">
                    <!-- Basic Info -->
                    <div class="grid grid-cols-2 gap-4">
                        <div class="form-control w-full col-span-2">
                            <label class="label pt-0"><span class="label-text text-[10px] font-black uppercase opacity-50">Nombre del Combo</span></label>
                            <input type="text" placeholder="Ej: Super Pack Familiar" class="input input-bordered font-bold" bind:value={comboName} />
                        </div>
                        <div class="form-control w-full">
                            <label class="label"><span class="label-text text-[10px] font-black uppercase opacity-50 text-secondary">Precio Especial Combo</span></label>
                            <div class="join">
                                <span class="btn join-item no-animation bg-base-200">$</span>
                                <input type="number" class="input input-bordered join-item w-full font-mono font-bold" bind:value={comboPrice} />
                            </div>
                        </div>
                        <div class="form-control w-full">
                            <label class="label"><span class="label-text text-[10px] font-black uppercase opacity-50">URL Imagen (Opcional)</span></label>
                            <input type="text" class="input input-bordered" bind:value={comboImageUrl} />
                        </div>
                    </div>

                    <div class="form-control w-full">
                        <label class="label"><span class="label-text text-[10px] font-black uppercase opacity-50">Descripción Corta</span></label>
                        <textarea class="textarea textarea-bordered h-20 text-sm" placeholder="Incluye bebida y guarnición..." bind:value={comboDescription}></textarea>
                    </div>

                    <!-- Selected Items List -->
                    <div class="flex-1 flex flex-col gap-3 min-h-0">
                        <h3 class="text-[10px] font-black uppercase tracking-[0.2em] opacity-40 flex items-center gap-2">
                            <span class="w-1.5 h-1.5 rounded-full bg-secondary"></span>
                            Artículos en este Combo
                        </h3>
                        <div class="flex-1 overflow-y-auto pr-2 flex flex-col gap-2">
                            {#if selectedItems.length === 0}
                                <div class="h-full flex flex-col items-center justify-center opacity-30 italic text-sm text-center px-10">
                                    <p>No has añadido productos aún.</p>
                                    <p class="text-[10px] not-italic font-bold uppercase mt-2">Selecciona productos de la izquierda</p>
                                </div>
                            {:else}
                                {#each selectedItems as item}
                                    <div class="flex items-center gap-3 p-3 bg-base-200/50 rounded-2xl border border-transparent hover:border-secondary/20 transition-all">
                                        <div class="flex-1">
                                            <p class="font-bold text-sm uppercase">{item.product.name}</p>
                                            <p class="text-[10px] opacity-40 font-mono italic">Original: ${item.product.price.toFixed(2)}</p>
                                        </div>
                                        <div class="flex items-center gap-2 bg-base-100 p-1 rounded-xl shadow-sm border border-base-300">
                                            <button class="btn btn-ghost btn-xs btn-square" onclick={() => updateQuantity(item.product.id!, -1)}>-</button>
                                            <span class="text-xs font-black px-1 min-w-[20px] text-center">{item.quantity}</span>
                                            <button class="btn btn-ghost btn-xs btn-square" onclick={() => updateQuantity(item.product.id!, 1)}>+</button>
                                        </div>
                                        <button class="btn btn-ghost btn-sm btn-circle text-error hover:bg-error/10" onclick={() => item.product.id && removeItem(item.product.id)}>
                                            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                                        </button>
                                    </div>
                                {/each}
                            {/if}
                        </div>
                    </div>
                </div>
            </div>

            <!-- Footer -->
            <div class="p-6 bg-base-100 border-t border-base-200 flex justify-end gap-3">
                <Button variant="ghost" onclick={onClose}>Cancelar</Button>
                <Button 
                    variant="primary" 
                    class="px-12 font-black uppercase tracking-widest text-sm h-14 rounded-2xl shadow-xl shadow-primary/20"
                    onclick={handleSave}
                    isLoading={isLoading}
                    disabled={selectedItems.length === 0}
                >
                    Guardar Combo
                </Button>
            </div>
        </div>
    </div>
{/if}

<style>
    .overflow-y-auto::-webkit-scrollbar {
        width: 4px;
    }
    .overflow-y-auto::-webkit-scrollbar-thumb {
        background: rgba(0,0,0,0.1);
        border-radius: 10px;
    }
</style>
