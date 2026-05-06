<script lang="ts">
	import { fade, slide, scale } from 'svelte/transition';
	import type { InventoryCategory } from '$lib/api/ingredients';

	let { 
		categories = [], 
		selectedIds = $bindable([]), 
		onCreate = (name: string) => {},
		onDelete = (id: number) => {}
	} = $props();

	let isOpen = $state(false);
	let searchQuery = $state('');
	let container: HTMLElement;

	let filtered = $derived(
		categories.filter(c => 
			c.name.toLowerCase().includes(searchQuery.toLowerCase())
		)
	);

	let showCreate = $derived(
		searchQuery.trim() !== '' && 
		!categories.some(c => c.name.toLowerCase() === searchQuery.toLowerCase().trim())
	);

	function toggle(id: number) {
		if (selectedIds.includes(id)) {
			selectedIds = selectedIds.filter(i => i !== id);
		} else {
			selectedIds = [...selectedIds, id];
		}
	}

	function handleCreate() {
		if (searchQuery.trim()) {
			onCreate(searchQuery.trim());
			searchQuery = '';
		}
	}

	// Cerrar al clickear fuera
	function handleOutsideClick(e: MouseEvent) {
		if (isOpen && container && !container.contains(e.target as Node)) {
			isOpen = false;
		}
	}
</script>

<svelte:window onclick={handleOutsideClick} />

<div class="relative inline-block text-left w-full md:w-64" bind:this={container}>
	<!-- TRIGGER -->
	<button 
		type="button"
		class="flex items-center justify-between w-full px-6 py-3 bg-base-100 border-2 border-base-200 rounded-[1.5rem] font-black text-sm hover:border-primary/30 transition-all group"
		onclick={() => isOpen = !isOpen}
	>
		<div class="flex items-center gap-2 truncate">
			<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 opacity-40 group-hover:opacity-100 transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
			</svg>
			<span class="truncate">
				{selectedIds.length === 0 ? 'Todas las Categorías' : `${selectedIds.length} Seleccionadas`}
			</span>
		</div>
		<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 transition-transform duration-300 {isOpen ? 'rotate-180' : ''}" fill="none" viewBox="0 0 24 24" stroke="currentColor">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
		</svg>
	</button>

	<!-- DROPDOWN -->
	{#if isOpen}
		<div 
			class="absolute z-[100] mt-3 w-72 bg-base-100 border border-base-200 shadow-[0_20px_50px_rgba(0,0,0,0.2)] rounded-[2rem] overflow-hidden origin-top"
			in:scale={{ duration: 200, start: 0.95, opacity: 0 }}
			out:fade={{ duration: 150 }}
		>
			<!-- SEARCH BAR -->
			<div class="p-4 bg-base-200/30 border-b border-base-200">
				<div class="relative">
					<input 
						type="text" 
						bind:value={searchQuery}
						placeholder="Buscar o crear..." 
						class="w-full bg-base-100 border-none rounded-xl px-4 py-2 text-sm font-bold focus:ring-2 focus:ring-primary/20 outline-none transition-all"
						autofocus
					/>
					{#if searchQuery}
						<button 
							class="absolute right-3 top-1/2 -translate-y-1/2 text-xs opacity-40 hover:opacity-100"
							onclick={() => searchQuery = ''}
						>✕</button>
					{/if}
				</div>
			</div>

			<!-- LIST -->
			<div class="max-h-72 overflow-y-auto p-2 scrollbar-thin scrollbar-thumb-base-300">
				{#each filtered as cat (cat.id)}
					<div 
						class="flex items-center justify-between p-3 rounded-2xl cursor-pointer transition-all {selectedIds.includes(cat.id!) ? 'bg-primary/5' : 'hover:bg-base-200/50'} group/item"
						onclick={() => toggle(cat.id!)}
					>
						<div class="flex items-center gap-3">
							<div class="w-5 h-5 rounded-lg border-2 flex items-center justify-center transition-all {selectedIds.includes(cat.id!) ? 'bg-primary border-primary' : 'border-base-300'}">
								{#if selectedIds.includes(cat.id!)}
									<svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
									</svg>
								{/if}
							</div>
							<span class="text-sm font-bold {selectedIds.includes(cat.id!) ? 'text-primary' : 'opacity-70'}">{cat.name}</span>
						</div>
						
						<button 
							class="btn btn-ghost btn-xs btn-circle text-error opacity-0 group-hover/item:opacity-100 transition-all hover:bg-error/10"
							onclick={(e) => { e.stopPropagation(); onDelete(cat.id!); }}
						>
							<svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
							</svg>
						</button>
					</div>
				{:else}
					{#if !showCreate}
						<div class="p-8 text-center opacity-30 italic text-xs">No se encontraron resultados</div>
					{/if}
				{/each}

				{#if showCreate}
					<button 
						class="w-full mt-1 p-4 rounded-2xl border-2 border-dashed border-primary/20 text-primary hover:bg-primary/5 hover:border-primary/40 transition-all flex items-center justify-center gap-2 group/btn"
						onclick={handleCreate}
					>
						<span class="text-lg group-hover/btn:scale-125 transition-transform">+</span>
						<span class="font-black text-xs uppercase tracking-widest">Crear "{searchQuery}"</span>
					</button>
				{/if}
			</div>

			<!-- FOOTER -->
			{#if selectedIds.length > 0}
				<div class="p-3 bg-base-200/30 border-t border-base-200 flex justify-between items-center" transition:slide>
					<span class="text-[10px] font-black opacity-40 uppercase tracking-widest pl-2">{selectedIds.length} seleccionadas</span>
					<button 
						class="btn btn-ghost btn-xs font-black text-primary hover:bg-primary/10 rounded-lg px-3"
						onclick={() => selectedIds = []}
					>Limpiar</button>
				</div>
			{/if}
		</div>
	{/if}
</div>
