<script lang="ts">
	import { IngredientService, type Ingredient, type InventoryCategory } from '$lib/api/ingredients';
	import { ProductService, type ModifierGroup } from '$lib/api/products';
	import { onMount } from 'svelte';
	import { posSocket } from '$lib/pos_socket.svelte';
	
	import Button from '$lib/components/ui/Button.svelte';
	
	// Componentes
	import IngredientModal from '$lib/components/inventory/IngredientModal.svelte';
	import InventoryAdjustmentModal from '$lib/components/inventory/InventoryAdjustmentModal.svelte';
	import InventoryCategoryModal from '$lib/components/inventory/InventoryCategoryModal.svelte';
	import ModifierGroupsManager from '$lib/components/inventory/ModifierGroupsManager.svelte';
	import InventoryGrid from '$lib/components/inventory/InventoryGrid.svelte';
	import InventoryList from '$lib/components/inventory/InventoryList.svelte';

	let ingredients = $state<Ingredient[]>([]);
	let totalIngredients = $state(0);
	let currentPage = $state(1);
	let pageSize = $state(20);
	let totalPages = $state(1);
	
	let inventoryCategories = $state<InventoryCategory[]>([]);
	
	let searchQuery = $state('');
	let searchInput = $state(''); 
	let stockStatus = $state<'all' | 'low' | 'none' | 'expiring'>('all');
	
	let selectedCategoryIds = $state<number[]>([]);
	let viewMode = $state<'grid' | 'list'>('grid');
	let isLoading = $state(true);
	let error = $state('');

	// Estado de Modales
	let isIngredientModalOpen = $state(false);
	let isAdjustmentModalOpen = $state(false);
	let isCategoryModalOpen = $state(false);
	let isGroupsManagerOpen = $state(false);

	let editingIngredient = $state<Ingredient | null>(null);
	let selectedIngredientForAdjustment = $state<Ingredient | null>(null);
	let adjustmentType = $state<'IN' | 'OUT' | 'SET'>('OUT');

	async function loadIngredients() {
		try {
			isLoading = true;
			const res = await IngredientService.getIngredients({
				search: searchQuery,
				category_ids: selectedCategoryIds.length > 0 ? selectedCategoryIds : undefined,
				stock_status: stockStatus !== 'all' ? stockStatus : undefined,
				limit: pageSize,
				offset: (currentPage - 1) * pageSize
			});
			ingredients = res.items;
			totalIngredients = res.total;
			totalPages = res.pages;
			error = '';
		} catch (e: any) {
			console.error('Error cargando ingredientes:', e);
			error = 'Error al cargar ingredientes';
		} finally {
			isLoading = false;
		}
	}

	async function loadCategories() {
		try {
			inventoryCategories = await IngredientService.getCategories();
		} catch (e: any) {
			console.error('Error cargando categorías:', e);
		}
	}

	async function handleDeleteIngredient(id: number) {
		if (!confirm('¿Eliminar este ingrediente?')) return;
		try {
			await IngredientService.delete(id);
			ingredients = ingredients.filter(i => i.id !== id);
		} catch (e: any) {
			alert('Error: ' + e.message);
		}
	}

	onMount(() => {
		loadCategories();
		posSocket.subscribe('inventory');
	});

	// Debounce effect para searchInput -> searchQuery
	$effect(() => {
		const val = searchInput;
		const timer = setTimeout(() => {
			searchQuery = val;
		}, 300);
		return () => clearTimeout(timer);
	});

	// Reaccionar a cambios en filtros para recargar
	$effect(() => {
		// Accedemos a los estados para que el efecto sea reactivo
		searchQuery;
		selectedCategoryIds;
		stockStatus;
		currentPage;
		pageSize;
		posSocket.ingredients;

		loadIngredients();
	});

	function toggleCategoryFilter(id: number) {
		if (selectedCategoryIds.includes(id)) {
			selectedCategoryIds = selectedCategoryIds.filter(cid => cid !== id);
		} else {
			selectedCategoryIds = [...selectedCategoryIds, id];
		}
		currentPage = 1;
	}

</script>

<div class="p-6 md:p-8 lg:p-10 flex flex-col gap-8 w-full flex-1 min-h-0 overflow-y-auto">
    <!-- ── Toolbar unificada estilo POS ────────────────────────────────────────── -->
    <div class="flex items-center justify-between bg-base-100 shadow-sm p-2 rounded-xl border border-base-200">
        <!-- Center: Search Input -->
        <div class="relative w-full md:w-48 lg:w-96 shrink-0 mx-2 hidden md:block">
            <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 opacity-20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
            </div>
            <input 
                type="text" 
                bind:value={searchInput}
                placeholder="Buscar materiales..." 
                class="input input-sm w-full pl-10 rounded-xl bg-base-200/40 backdrop-blur-md border border-base-300 focus:ring-2 focus:ring-primary/20 transition-all font-bold text-sm"
            />
        </div>

        <!-- Right: Filters & Actions -->
        <div class="flex items-center gap-2 pl-4 border-l border-base-200">
            <!-- Filtros Dropdown -->
            <div class="dropdown dropdown-bottom dropdown-end">
                <div tabindex="0" role="button" class="btn btn-sm bg-base-100 border-2 border-base-200 px-4 font-black flex items-center gap-2 hover:border-primary/30 transition-all rounded-xl shadow-sm">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                    </svg>
                    Filtros
                    {#if selectedCategoryIds.length > 0 || stockStatus !== 'all'}
                        <span class="badge badge-primary badge-xs p-1 font-black shadow-sm">!</span>
                    {/if}
                </div>
                <div tabindex="0" class="dropdown-content z-[50] card card-compact w-72 p-2 shadow-2xl bg-base-100 border border-base-200 mt-3 rounded-2xl">
                    <div class="p-3 border-b border-base-200 mb-2">
                        <span class="text-[10px] uppercase font-black opacity-40 tracking-widest block mb-2">Estado de Stock</span>
                        <div class="grid grid-cols-2 gap-1">
                            <button class="btn btn-xs {stockStatus === 'all' ? 'btn-primary' : 'btn-ghost'} rounded-lg font-bold" onclick={() => stockStatus = 'all'}>Todos</button>
                            <button class="btn btn-xs {stockStatus === 'low' ? 'bg-warning text-white' : 'btn-ghost'} rounded-lg font-bold" onclick={() => stockStatus = 'low'}>Bajo Stock</button>
                            <button class="btn btn-xs {stockStatus === 'none' ? 'bg-error text-white' : 'btn-ghost'} rounded-lg font-bold" onclick={() => stockStatus = 'none'}>Agotado</button>
                            <button class="btn btn-xs {stockStatus === 'expiring' ? 'bg-info text-white' : 'btn-ghost'} rounded-lg font-bold" onclick={() => stockStatus = 'expiring'}>Caduca</button>
                        </div>
                    </div>
                    <div class="p-3 border-b border-base-200 mb-2">
                        <div class="flex justify-between items-center mb-2">
                            <span class="text-[10px] uppercase font-black opacity-40 tracking-widest">Categorías</span>
                            <button class="text-[10px] font-black text-primary hover:underline" onclick={() => selectedCategoryIds = []}>Limpiar</button>
                        </div>
                        <div class="max-h-48 overflow-y-auto space-y-1 pr-1 elegant-scroll">
                            {#each inventoryCategories as cat}
                                <div class="flex items-center gap-3 p-2 rounded-xl hover:bg-base-200 transition-colors cursor-pointer" onclick={() => toggleCategoryFilter(cat.id!)}>
                                    <input type="checkbox" checked={selectedCategoryIds.includes(cat.id!)} class="checkbox checkbox-primary checkbox-xs rounded-md" onchange={() => {}} />
                                    <span class="font-bold text-xs">{cat.name}</span>
                                </div>
                            {/each}
                        </div>
                    </div>
                    <div class="p-1">
                        <button class="btn btn-xs btn-ghost w-full font-black text-primary text-[9px] uppercase tracking-tighter" onclick={() => isCategoryModalOpen = true}>⚙️ Categorías</button>
                    </div>
                </div>
            </div>

            <!-- View Mode Toggle -->
            <div class="flex items-center gap-1 bg-base-200 p-1 rounded-xl">
                <button class="btn btn-xs btn-circle {viewMode === 'grid' ? 'bg-primary text-white shadow-md' : 'btn-ghost opacity-40'}" onclick={() => viewMode = 'grid'}>
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" /></svg>
                </button>
                <button class="btn btn-xs btn-circle {viewMode === 'list' ? 'bg-primary text-white shadow-md' : 'btn-ghost opacity-40'}" onclick={() => viewMode = 'list'}>
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" /></svg>
                </button>
            </div>

            <Button 
                variant="outline" 
                size="sm" 
                class="rounded-xl font-black gap-1.5 px-4" 
                onclick={() => isGroupsManagerOpen = true}
            >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16m-7 6h7" /></svg>
                Grupos
            </Button>

            <Button 
                variant="primary" 
                size="sm" 
                class="rounded-xl font-black gap-1.5 px-4 shadow-md" 
                onclick={() => { editingIngredient = null; isIngredientModalOpen = true; }}
            >
                <span class="text-lg leading-none">+</span>
                Insumo
            </Button>
        </div>
    </div>

    <!-- Mobile Search -->
    <div class="md:hidden w-full relative">
        <input 
            type="text" 
            bind:value={searchInput}
            placeholder="Buscar..." 
            class="input input-md w-full pl-10 rounded-xl bg-base-100 border-2 border-base-200 focus:ring-2 focus:ring-primary/20 transition-all font-bold"
        />
    </div>

    {#if error}
        <div class="alert alert-error rounded-2xl shadow-lg border-none bg-error/20 text-error-content font-bold">
            <span class="text-xl">⚠️</span>
            <span>{error}</span>
            <button class="btn btn-sm btn-ghost" onclick={loadAllData}>Reintentar</button>
        </div>
    {/if}

		{#if selectedCategoryIds.length > 0 || searchQuery || stockStatus !== 'all'}
			<div class="flex flex-wrap items-center gap-2 mt-4 animate-in slide-in-from-top-2 duration-300">
				<span class="text-[10px] font-black opacity-30 uppercase tracking-widest mr-2">Filtros activos:</span>
				{#if stockStatus !== 'all'}
					<div class="badge badge-secondary rounded-full px-4 py-3 font-black flex items-center gap-2 shadow-sm border-2">
						Estado: {stockStatus === 'low' ? 'Bajo Stock' : stockStatus === 'none' ? 'Agotado' : 'Próximo a Vencer'}
						<button class="hover:text-error transition-colors" onclick={() => stockStatus = 'all'}>✕</button>
					</div>
				{/if}
				{#each selectedCategoryIds as sid}
					{@const cat = inventoryCategories.find(c => c.id === sid)}
					{#if cat && cat.name.toLowerCase() !== 'insumo'}
						<div class="badge badge-primary badge-outline rounded-full px-4 py-3 font-black flex items-center gap-2 shadow-sm border-2">
							{cat.name}
							<button class="hover:text-error transition-colors" onclick={() => toggleCategoryFilter(sid)}>✕</button>
						</div>
					{/if}
				{/each}
				{#if searchQuery}
					<div class="badge badge-ghost rounded-full px-4 py-3 font-black flex items-center gap-2 border-2 border-base-300">
						Buscando: "{searchQuery}"
						<button class="hover:text-error transition-colors" onclick={() => { searchQuery = ''; searchInput = ''; }}>✕</button>
					</div>
				{/if}
				<button class="btn btn-link btn-xs font-black opacity-40 hover:opacity-100" onclick={() => { selectedCategoryIds = []; searchQuery = ''; searchInput = ''; stockStatus = 'all'; }}>Limpiar todo</button>
			</div>
		{/if}

		<div class="mb-6"></div>

		{#if isLoading}
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
				{#each Array(6) as _}
					<div class="h-32 bg-base-300 animate-pulse rounded-2xl"></div>
				{/each}
			</div>
		{:else if ingredients.length === 0}
			<div class="flex flex-col items-center justify-center py-20 bg-base-100 rounded-[2rem] border border-dashed border-base-300">
				<span class="text-6xl mb-4">📦</span>
				<h3 class="text-xl font-black opacity-40 uppercase tracking-widest">Sin materiales encontrados</h3>
				<p class="text-sm opacity-30 mt-2">Prueba ajustando los filtros o el buscador.</p>
				<Button variant="ghost" class="mt-6" onclick={() => { searchQuery = ''; selectedCategoryIds = []; }}>Limpiar Filtros</Button>
			</div>
		{:else if viewMode === 'grid'}
			<InventoryGrid 
				{ingredients} 
				categories={inventoryCategories} 
				onAdjust={(ing) => { selectedIngredientForAdjustment = ing; adjustmentType = 'IN'; isAdjustmentModalOpen = true; }}
				onEdit={(ing) => { editingIngredient = ing; isIngredientModalOpen = true; }}
				onDelete={handleDeleteIngredient}
			/>
		{:else}
			<InventoryList 
				{ingredients} 
				categories={inventoryCategories} 
				onAdjust={(ing) => { selectedIngredientForAdjustment = ing; adjustmentType = 'IN'; isAdjustmentModalOpen = true; }}
				onEdit={(ing) => { editingIngredient = ing; isIngredientModalOpen = true; }}
				onDelete={handleDeleteIngredient}
			/>
		{/if}

		{#if totalPages > 1}
			<div class="flex flex-col md:flex-row justify-between items-center mt-8 gap-4 pb-10">
				<p class="text-xs font-bold opacity-40 uppercase tracking-widest">
					Mostrando {((currentPage - 1) * pageSize) + 1}-{Math.min(currentPage * pageSize, totalIngredients)} de {totalIngredients} materiales
				</p>
				<div class="join bg-base-100 shadow-sm border border-base-200 rounded-2xl overflow-hidden">
					<button 
						class="join-item btn btn-sm btn-ghost px-4 font-black transition-all" 
						disabled={currentPage === 1}
						onclick={() => currentPage--}
					>Anterior</button>
					<button class="join-item btn btn-sm btn-disabled px-4 font-black bg-primary/10 text-primary">{currentPage} / {totalPages}</button>
					<button 
						class="join-item btn btn-sm btn-ghost px-4 font-black transition-all" 
						disabled={currentPage === totalPages}
						onclick={() => currentPage++}
					>Siguiente</button>
				</div>
				<select 
					bind:value={pageSize} 
					class="select select-bordered select-sm rounded-xl font-bold bg-base-100"
					onchange={() => currentPage = 1}
				>
					<option value={10}>10 por pág.</option>
					<option value={20}>20 por pág.</option>
					<option value={50}>50 por pág.</option>
				</select>
			</div>
		{/if}
</div>

<!-- Modales Extraídos -->
<IngredientModal 
	isOpen={isIngredientModalOpen} 
	ingredient={editingIngredient} 
	categories={inventoryCategories} 
	onClose={() => isIngredientModalOpen = false} 
	onSave={() => loadIngredients()}
/>

<InventoryAdjustmentModal 
	isOpen={isAdjustmentModalOpen} 
	ingredient={selectedIngredientForAdjustment} 
	initialType={adjustmentType}
	onClose={() => isAdjustmentModalOpen = false} 
	onSave={() => loadIngredients()}
/>

<InventoryCategoryModal 
	isOpen={isCategoryModalOpen} 
	categories={inventoryCategories} 
	onClose={() => isCategoryModalOpen = false} 
	onRefresh={() => loadCategories()}
/>

<ModifierGroupsManager 
	isOpen={isGroupsManagerOpen} 
	onClose={() => isGroupsManagerOpen = false} 
/>
