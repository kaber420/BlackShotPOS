<script lang="ts">
    import { onMount } from 'svelte';
    import { ProductService } from '$lib/api/products';
    import type { Product } from '$lib/api/products';
    import { CategoryService } from '$lib/api/categories';
    import type { Category } from '$lib/api/categories';
    
    // Components
    import ProductModal from '$lib/components/ProductModal.svelte';
    import CategoryModal from '$lib/components/CategoryModal.svelte';
    import MeasureModal from '$lib/components/MeasureModal.svelte';
    import ComboBuilderModal from '$lib/components/product/ComboBuilderModal.svelte';
    import Button from '$lib/components/ui/Button.svelte';
    import ProductGrid from '$lib/components/menu/ProductGrid.svelte';
    import ProductList from '$lib/components/menu/ProductList.svelte';
    import Toolbar from '$lib/components/ui/Toolbar.svelte';

    let products = $state<Product[]>([]);
    let categories = $state<Category[]>([]);
    let isLoading = $state(true);
    let searchQuery = $state('');
    let selectedCategoryIds = $state<number[]>([]);
    let viewMode = $state<'grid' | 'list'>('list');
    let errorMessage = $state('');

    // Modal states
    let isProductModalOpen = $state(false);
    let isCategoryModalOpen = $state(false);
    let isMeasureModalOpen = $state(false);
    let isComboModalOpen = $state(false);
    let editingProduct = $state<Partial<Product> | null>(null);

    const filteredProducts = $derived(
        products.filter(p => {
            const matchesSearch = p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                                 p.description?.toLowerCase().includes(searchQuery.toLowerCase());
            const matchesCategory = selectedCategoryIds.length === 0 || 
                                   (p.category_id && selectedCategoryIds.includes(p.category_id));
            return matchesSearch && matchesCategory;
        })
    );

    async function loadData() {
        isLoading = true;
        errorMessage = '';
        try {
            const [fetchedProducts, fetchedCategories] = await Promise.all([
                ProductService.getAll(undefined, true),
                CategoryService.getAll()
            ]);
            products = fetchedProducts;
            categories = fetchedCategories;
        } catch (error) {
            console.error('Error loading menu data:', error);
            errorMessage = 'No se pudieron cargar los datos del menú.';
        } finally {
            isLoading = false;
        }
    }

    function toggleCategoryFilter(id: number) {
        if (selectedCategoryIds.includes(id)) {
            selectedCategoryIds = selectedCategoryIds.filter(cid => cid !== id);
        } else {
            selectedCategoryIds = [...selectedCategoryIds, id];
        }
    }

    function openCreateModal() {
        editingProduct = null;
        isProductModalOpen = true;
    }

    function openEditModal(product: Product) {
        editingProduct = { ...product };
        isProductModalOpen = true;
    }

    async function deleteProduct(id: number) {
        if (!confirm('¿Estás seguro de que deseas eliminar este producto?')) return;
        
        try {
            await ProductService.delete(id);
            await loadData();
        } catch (error) {
            console.error('Error deleting product:', error);
            errorMessage = 'No se pudo eliminar el producto.';
        }
    }

    let viewModeInitialized = false;

    onMount(() => {
        const savedViewMode = localStorage.getItem('pos_menu_view_mode');
        if (savedViewMode === 'grid' || savedViewMode === 'list') {
            viewMode = savedViewMode;
        }
        viewModeInitialized = true;
        loadData();
    });

    $effect(() => {
        if (viewModeInitialized) {
            localStorage.setItem('pos_menu_view_mode', viewMode);
        }
    });
</script>

<div class="p-6 md:p-8 lg:p-10 flex flex-col gap-8 w-full flex-1 min-h-0 overflow-y-auto">
    <Toolbar title="Menú">
        {#snippet left()}
            <!-- Search Compacto -->
            <div class="relative w-full max-w-xs group hidden sm:block">
                <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 opacity-30 group-focus-within:opacity-100 transition-all" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                </div>
                <input 
                    type="text" 
                    bind:value={searchQuery}
                    placeholder="Buscar producto..." 
                    class="input input-sm w-full pl-9 rounded-xl bg-base-200/40 backdrop-blur-md border border-base-300 focus:ring-2 focus:ring-primary/20 transition-all font-bold text-sm"
                />
            </div>

            <!-- Category Filter Dropdown -->
            <div class="dropdown dropdown-bottom">
                <div tabindex="0" role="button" class="btn btn-sm bg-base-100 border-2 border-base-200 px-4 font-black flex items-center gap-2 hover:border-primary/30 transition-all rounded-xl shadow-sm">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" /></svg>
                    Categorías
                    {#if selectedCategoryIds.length > 0}
                        <span class="badge badge-primary badge-sm font-black scale-75">{selectedCategoryIds.length}</span>
                    {/if}
                </div>
                <div tabindex="0" class="dropdown-content z-[60] card card-compact w-64 p-2 shadow-2xl bg-base-100 border border-base-200 mt-3 rounded-2xl animate-in zoom-in-95 duration-200">
                    <div class="p-3 border-b border-base-200 mb-2 flex justify-between items-center">
                        <span class="text-[10px] uppercase font-black opacity-40 tracking-widest">Filtrar por Categoría</span>
                        <button class="text-[10px] font-black text-primary hover:underline" onclick={() => selectedCategoryIds = []}>Limpiar</button>
                    </div>
                    <div class="max-h-60 overflow-y-auto space-y-1 p-1 elegant-scroll">
                        {#each categories as cat}
                            <div class="flex items-center gap-3 p-2 rounded-xl hover:bg-base-200 transition-colors cursor-pointer" onclick={() => toggleCategoryFilter(cat.id!)}>
                                <input 
                                    type="checkbox" 
                                    checked={selectedCategoryIds.includes(cat.id!)} 
                                    class="checkbox checkbox-primary checkbox-sm rounded-lg"
                                    onchange={() => {}} 
                                />
                                <span class="font-bold text-sm">{cat.name}</span>
                            </div>
                        {:else}
                            <div class="p-4 text-center opacity-40 text-xs italic">No hay categorías</div>
                        {/each}
                    </div>

                </div>
            </div>
        {/snippet}

        {#snippet right()}
            <!-- View Mode Toggle -->
            <div class="flex items-center bg-base-200 p-1 rounded-xl gap-1 mr-2 hidden md:flex">
                <button 
                    class="btn btn-xs btn-circle {viewMode === 'grid' ? 'btn-primary shadow-sm' : 'btn-ghost opacity-40'}"
                    onclick={() => viewMode = 'grid'}
                >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" /></svg>
                </button>
                <button 
                    class="btn btn-xs btn-circle {viewMode === 'list' ? 'btn-primary shadow-sm' : 'btn-ghost opacity-40'}"
                    onclick={() => viewMode = 'list'}
                >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" /></svg>
                </button>
            </div>

            <!-- More Actions Dropdown -->
            <div class="dropdown dropdown-end">
                <div tabindex="0" role="button" class="btn btn-sm btn-circle btn-ghost">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" /></svg>
                </div>
                <div tabindex="0" class="dropdown-content z-[60] card card-compact w-52 p-2 shadow-2xl bg-base-100 border border-base-200 mt-2 rounded-2xl">
                    <button class="flex items-center gap-3 p-3 rounded-xl hover:bg-base-200 transition-colors font-bold text-sm text-left" onclick={() => isMeasureModalOpen = true}>
                        <span>📏</span> Medidas
                    </button>
                    <button class="flex items-center gap-3 p-3 rounded-xl hover:bg-base-200 transition-colors font-bold text-sm text-left" onclick={() => isCategoryModalOpen = true}>
                        <span>📁</span> Categorías
                    </button>
                </div>
            </div>

            <Button variant="ghost" size="sm" class="rounded-xl px-4 font-black text-xs shrink-0 border border-base-200" onclick={() => isComboModalOpen = true}>
                + COMBO
            </Button>

            <Button variant="primary" size="sm" class="rounded-xl px-4 font-black text-xs shrink-0" onclick={openCreateModal}>
                + PRODUCTO
            </Button>
        {/snippet}
    </Toolbar>
 
    <!-- Mobile Search -->
    <div class="md:hidden w-full relative">
        <input 
            type="text" 
            bind:value={searchQuery}
            placeholder="Buscar producto..." 
            class="input input-md w-full pl-10 rounded-xl bg-base-100 border-2 border-base-200 focus:ring-2 focus:ring-primary/20 transition-all font-bold"
        />
    </div>

    {#if errorMessage}
        <div class="alert alert-error rounded-2xl shadow-lg border-none bg-error/20 text-error-content font-bold animate-in slide-in-from-top duration-300">
            <span class="text-xl">⚠️</span>
            <span>{errorMessage}</span>
            <button class="btn btn-sm btn-ghost" onclick={loadData}>Reintentar</button>
        </div>
    {/if}

    <!-- Active Filter Chips -->
    {#if selectedCategoryIds.length > 0 || searchQuery}
        <div class="flex flex-wrap items-center gap-2 animate-in slide-in-from-top-2 duration-300">
            <span class="text-[10px] font-black opacity-30 uppercase tracking-widest mr-2">Filtros:</span>
            {#each selectedCategoryIds as sid}
                {@const cat = categories.find(c => c.id === sid)}
                {#if cat}
                    <div class="badge badge-primary badge-outline rounded-lg px-3 py-3 font-black flex items-center gap-2 border-2 text-[10px] uppercase">
                        {cat.name}
                        <button class="hover:text-error transition-colors" onclick={() => toggleCategoryFilter(sid)}>✕</button>
                    </div>
                {/if}
            {/each}
            {#if searchQuery}
                <div class="badge badge-ghost rounded-lg px-3 py-3 font-black flex items-center gap-2 border-2 border-base-300 text-[10px] uppercase">
                    🔍 "{searchQuery}"
                    <button class="hover:text-error transition-colors" onclick={() => searchQuery = ''}>✕</button>
                </div>
            {/if}
            <button class="btn btn-link btn-xs font-black opacity-40 hover:opacity-100 text-[10px] uppercase no-underline" onclick={() => { selectedCategoryIds = []; searchQuery = ''; }}>Limpiar todo</button>
        </div>
    {/if}

    <div class="flex-1 min-h-0">
        {#if isLoading}
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {#each Array(8) as _}
                    <div class="h-56 bg-base-200/50 animate-pulse rounded-2xl"></div>
                {/each}
            </div>
        {:else if filteredProducts.length === 0}
            <div class="flex flex-col items-center justify-center py-32 bg-base-100 rounded-[2rem] border-2 border-dashed border-base-200 animate-in fade-in duration-500">
                <span class="text-6xl mb-6 grayscale opacity-20">🍽️</span>
                <h3 class="text-xl font-black opacity-40 uppercase tracking-widest">Sin resultados</h3>
                <p class="text-sm opacity-20 mt-2 font-bold uppercase tracking-tighter">Ajusta los filtros o el buscador para ver tus platillos.</p>
                <Button variant="ghost" class="mt-8 border border-base-200" onclick={() => { searchQuery = ''; selectedCategoryIds = []; }}>Limpiar Filtros</Button>
            </div>
        {:else if viewMode === 'grid'}
            <ProductGrid 
                products={filteredProducts} 
                {categories}
                onEdit={openEditModal}
                onDelete={deleteProduct}
            />
        {:else}
            <ProductList 
                products={filteredProducts} 
                {categories}
                onEdit={openEditModal}
                onDelete={deleteProduct}
            />
        {/if}
    </div>
</div>

<ProductModal 
    isOpen={isProductModalOpen} 
    product={editingProduct} 
    {categories}
    onClose={() => isProductModalOpen = false} 
    onSave={loadData} 
/>

<CategoryModal 
    isOpen={isCategoryModalOpen} 
    onClose={() => isCategoryModalOpen = false} 
    onRefresh={loadData} 
/>

<MeasureModal
    isOpen={isMeasureModalOpen}
    onClose={() => isMeasureModalOpen = false}
    onRefresh={loadData}
/>

<ComboBuilderModal 
    isOpen={isComboModalOpen} 
    onClose={() => isComboModalOpen = false} 
    onSave={loadData} 
/>

<style>
    .elegant-scroll::-webkit-scrollbar {
        width: 4px;
    }
    .elegant-scroll::-webkit-scrollbar-track {
        background: transparent;
    }
    .elegant-scroll::-webkit-scrollbar-thumb {
        background: rgba(var(--bc), 0.1);
        border-radius: 10px;
    }
</style>
