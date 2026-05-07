<script lang="ts">
	import { IngredientService, type Ingredient, type InventoryCategory } from '$lib/api/ingredients';
	import { ProductService, type ModifierGroup } from '$lib/api/products';
	import { onMount } from 'svelte';
	import { posSocket } from '$lib/pos_socket.svelte';
	
	import Button from '$lib/components/ui/Button.svelte';
	
	// Nuevos Componentes
	import IngredientModal from '$lib/components/inventory/IngredientModal.svelte';
	import InventoryAdjustmentModal from '$lib/components/inventory/InventoryAdjustmentModal.svelte';
	import InventoryCategoryModal from '$lib/components/inventory/InventoryCategoryModal.svelte';
	import ModifierGroupModal from '$lib/components/inventory/ModifierGroupModal.svelte';
	import ModifierModal from '$lib/components/inventory/ModifierModal.svelte';
	import InventoryGrid from '$lib/components/inventory/InventoryGrid.svelte';
	import InventoryList from '$lib/components/inventory/InventoryList.svelte';

	let ingredients = $state<Ingredient[]>([]);
	let totalIngredients = $state(0);
	let currentPage = $state(1);
	let pageSize = $state(20);
	let totalPages = $state(1);
	
	let inventoryCategories = $state<InventoryCategory[]>([]);
	
	let searchQuery = $state('');
	let searchInput = $state(''); // Valor del input sin debounce
	let stockStatus = $state<'all' | 'low' | 'none' | 'expiring'>('all');
	
	let selectedCategoryIds = $state<number[]>([]);
	let viewMode = $state<'grid' | 'list'>('grid');
	let modifierGroups = $state<ModifierGroup[]>([]);
	let isLoading = $state(true);
	let activeTab = $state<'ingredients' | 'groups'>('ingredients');
	let error = $state('');

	// Debounce para la búsqueda
	let debounceTimer: any;
	$effect(() => {
		clearTimeout(debounceTimer);
		debounceTimer = setTimeout(() => {
			searchQuery = searchInput;
		}, 300);
	});

	// Estado de Modales
	let isIngredientModalOpen = $state(false);
	let isAdjustmentModalOpen = $state(false);
	let isCategoryModalOpen = $state(false);
	let isGroupModalOpen = $state(false);
	let isModifierModalOpen = $state(false);

	let editingIngredient = $state<Ingredient | null>(null);
	let selectedIngredientForAdjustment = $state<Ingredient | null>(null);
	let adjustmentType = $state<'IN' | 'OUT' | 'SET'>('OUT');
	let editingGroup = $state<ModifierGroup | null>(null);
	let selectedGroupId = $state<number | null>(null);

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

	async function loadGroups() {
		try {
			modifierGroups = await ProductService.getModifierGroups();
		} catch (e: any) {
			console.error('Error cargando grupos:', e);
		}
	}

	async function loadCategories() {
		try {
			inventoryCategories = await IngredientService.getCategories();
		} catch (e: any) {
			console.error('Error cargando categorías:', e);
		}
	}

	async function loadAllData() {
		await Promise.all([loadGroups(), loadCategories()]);
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

	async function handleDeleteGroup(id: number) {
		if (!confirm('¿Eliminar este grupo y sus opciones?')) return;
		try {
			await ProductService.deleteModifierGroup(id);
			modifierGroups = modifierGroups.filter(g => g.id !== id);
		} catch (e: any) {
			alert('Error: ' + e.message);
		}
	}

	async function handleDeleteModifier(id: number) {
		if (!confirm('¿Eliminar esta opción?')) return;
		try {
			await ProductService.deleteModifier(id);
			await loadAllData();
		} catch (e: any) {
			alert('Error: ' + e.message);
		}
	}

	onMount(() => {
		loadAllData();
		posSocket.subscribe('inventory');
	});

	$effect(() => {
		if (activeTab === 'ingredients') {
			searchQuery;
			selectedCategoryIds.length;
			stockStatus;
			currentPage;
			pageSize;
			posSocket.ingredients; 

			loadIngredients();
		}
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
	<div class="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
		<div>
			<h1 class="text-4xl font-black text-base-content tracking-tighter">Inventario Maestros</h1>
		</div>
    
    {#if error}
        <div class="alert alert-error mb-6 rounded-2xl shadow-lg border-none bg-error/20 text-error-content font-bold">
            <span class="text-xl">⚠️</span>
            <span>{error}</span>
            <button class="btn btn-sm btn-ghost" onclick={loadAllData}>Reintentar</button>
        </div>
    {/if}
		
		<div class="tabs tabs-boxed bg-base-200 p-1 rounded-xl">
			<button class="tab tab-md transition-all duration-300 {activeTab === 'ingredients' ? 'tab-active bg-primary text-primary-content shadow-md' : ''}" onclick={() => activeTab = 'ingredients'}>
				Materiales
			</button>
			<button class="tab tab-md transition-all duration-300 {activeTab === 'groups' ? 'tab-active bg-secondary text-secondary-content shadow-md' : ''}" onclick={() => activeTab = 'groups'}>
				Grupos de Opciones
			</button>
		</div>
	</div>

	{#if activeTab === 'ingredients'}
		<div class="flex flex-col md:flex-row gap-4 items-center justify-between">
			<div class="flex flex-col md:flex-row gap-4 w-full md:w-auto items-center">
				<div class="relative w-full md:w-80 group">
					<div class="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none">
						<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 opacity-20 group-focus-within:opacity-100 group-focus-within:text-primary transition-all" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
						</svg>
					</div>
					<input 
						type="text" 
						bind:value={searchInput}
						placeholder="Buscar por nombre..." 
						class="input input-lg w-full pl-14 bg-base-100 border-2 border-base-200 rounded-[1.5rem] font-bold focus:border-primary/50 transition-all shadow-sm"
					/>
				</div>

				<!-- Filtro de Estado de Stock -->
				<div class="join bg-base-100 border-2 border-base-200 rounded-[1.5rem] p-1 shadow-sm overflow-hidden">
					<button 
						class="btn btn-sm join-item border-none {stockStatus === 'all' ? 'btn-primary' : 'btn-ghost opacity-40'} font-black text-[10px] uppercase tracking-widest px-4"
						onclick={() => { stockStatus = 'all'; currentPage = 1; }}
					>Todos</button>
					<button 
						class="btn btn-sm join-item border-none {stockStatus === 'low' ? 'bg-warning text-warning-content shadow-inner' : 'btn-ghost opacity-40'} font-black text-[10px] uppercase tracking-widest px-4"
						onclick={() => { stockStatus = 'low'; currentPage = 1; }}
					>Bajo</button>
					<button 
						class="btn btn-sm join-item border-none {stockStatus === 'none' ? 'bg-error text-error-content shadow-inner' : 'btn-ghost opacity-40'} font-black text-[10px] uppercase tracking-widest px-4"
						onclick={() => { stockStatus = 'none'; currentPage = 1; }}
					>Agotado</button>
					<button 
						class="btn btn-sm join-item border-none {stockStatus === 'expiring' ? 'bg-info text-info-content shadow-inner' : 'btn-ghost opacity-40'} font-black text-[10px] uppercase tracking-widest px-4"
						onclick={() => { stockStatus = 'expiring'; currentPage = 1; }}
					>Caduca</button>
				</div>

				<div class="dropdown dropdown-bottom">
					<div tabindex="0" role="button" class="btn btn-lg bg-base-100 border-2 border-base-200 px-6 font-black flex items-center gap-2 hover:border-primary/30 transition-all rounded-[1.5rem] shadow-sm">
						<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" /></svg>
						Filtrar
						<span class="text-xs opacity-40 ml-1 font-black">({totalIngredients})</span>
						{#if selectedCategoryIds.length > 0}
							<span class="badge badge-primary badge-sm font-black ml-1">{selectedCategoryIds.length}</span>
						{/if}
					</div>
					<div tabindex="0" class="dropdown-content z-[50] card card-compact w-64 p-2 shadow-2xl bg-base-100 border border-base-200 mt-3 rounded-2xl">
						<div class="p-3 border-b border-base-200 mb-2 flex justify-between items-center">
							<span class="text-[10px] uppercase font-black opacity-40 tracking-widest">Categorías</span>
							<button class="text-[10px] font-black text-primary hover:underline" onclick={() => selectedCategoryIds = []}>Limpiar</button>
						</div>
						<div class="max-h-60 overflow-y-auto space-y-1 p-1">
							{#each inventoryCategories as cat}
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
						<div class="p-2 mt-2 border-t border-base-200">
							<button 
								class="btn btn-sm btn-ghost w-full justify-center gap-2 font-black text-primary text-[10px] uppercase tracking-widest"
								onclick={() => isCategoryModalOpen = true}
							>
								⚙️ Gestionar Categorías
							</button>
						</div>
					</div>
				</div>
			</div>

			<div class="flex items-center gap-2 bg-base-200/50 p-1 rounded-[1.5rem]">
				<div class="flex items-center gap-1 mr-2 border-r border-base-300 pr-2">
					<button 
						class="btn btn-sm btn-circle {viewMode === 'grid' ? 'btn-primary shadow-sm' : 'btn-ghost opacity-40'}"
						onclick={() => viewMode = 'grid'}
					>
						<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" /></svg>
					</button>
					<button 
						class="btn btn-sm btn-circle {viewMode === 'list' ? 'btn-primary shadow-sm' : 'btn-ghost opacity-40'}"
						onclick={() => viewMode = 'list'}
					>
						<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" /></svg>
					</button>
				</div>
				<Button variant="primary" size="sm" class="rounded-full px-6 font-black" onclick={() => { editingIngredient = null; isIngredientModalOpen = true; }}>
					+ Insumo
				</Button>
			</div>
		</div>

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

	{:else}
		<div class="flex justify-between items-center mb-6">
			<h2 class="text-xl font-bold opacity-80 flex items-center gap-2">
				<div class="w-2 h-8 bg-secondary rounded-full"></div>
				Agrupaciones (Leches, Jarabes, etc.)
			</h2>
			<Button variant="secondary" onclick={() => { editingGroup = null; isGroupModalOpen = true; }}>
				+ Nuevo Grupo
			</Button>
		</div>

		<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
			{#each modifierGroups as group}
				<div class="bg-base-100 rounded-3xl border border-base-200 shadow-sm overflow-hidden flex flex-col">
					<div class="p-6 bg-base-200/50 border-b border-base-200 flex justify-between items-center">
						<div>
							<h3 class="font-black text-xl tracking-tight">{group.name}</h3>
							<p class="text-[10px] opacity-50 uppercase font-bold tracking-widest">
								{group.max_selection === 1 ? 'Selección Única' : `Máx ${group.max_selection} opciones`}
							</p>
						</div>
						<div class="flex gap-2">
							<Button variant="ghost" circle size="sm" onclick={() => { selectedGroupId = group.id!; isModifierModalOpen = true; }}>+</Button>
							<Button variant="danger" circle size="sm" onclick={() => handleDeleteGroup(group.id!)}>×</Button>
						</div>
					</div>
					
					<div class="p-4 flex flex-col gap-2">
						{#if !group.modifiers || group.modifiers.length === 0}
							<p class="text-center py-8 text-xs italic opacity-40 uppercase font-bold">Sin opciones añadidas</p>
						{:else}
							<div class="grid grid-cols-1 gap-2">
								{#each group.modifiers as mod}
									<div class="flex items-center justify-between bg-base-100 p-4 rounded-2xl border border-base-200 group/item">
										<div class="flex items-center gap-4">
											<div class="w-10 h-10 bg-secondary/10 rounded-xl flex items-center justify-center text-secondary font-black">
												{mod.name[0]}
											</div>
											<div>
												<p class="font-bold text-sm leading-tight">{mod.name}</p>
												<p class="text-[10px] opacity-40">
													Vinculado: {ingredients.find(i => i.id === mod.ingredient_id)?.name || 'Sin vincular'}
												</p>
											</div>
										</div>
										<div class="flex items-center gap-4">
											<span class="text-xs font-black opacity-60">
												{mod.extra_price > 0 ? `+$${mod.extra_price}` : 'Incluido'}
											</span>
											<Button variant="danger" square size="xs" class="opacity-0 group-hover/item:opacity-100" onclick={() => handleDeleteModifier(mod.id!)}>×</Button>
										</div>
									</div>
								{/each}
							</div>
						{/if}
					</div>
				</div>
			{/each}
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

<ModifierGroupModal 
	isOpen={isGroupModalOpen} 
	group={editingGroup} 
	onClose={() => isGroupModalOpen = false} 
	onSave={() => loadGroups()}
/>

<ModifierModal 
	isOpen={isModifierModalOpen} 
	groupId={selectedGroupId} 
	{ingredients} 
	onClose={() => isModifierModalOpen = false} 
	onSave={() => loadAllData()}
/>
