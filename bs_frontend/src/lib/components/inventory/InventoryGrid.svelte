<script lang="ts">
	import { type Ingredient, type InventoryCategory } from '$lib/api/ingredients';
	import { MEASURE_TYPES } from '$lib/constants/inventory';
	import { can } from '$lib/app_state.svelte';
	import Button from '$lib/components/ui/Button.svelte';

	interface Props {
		ingredients: Ingredient[];
		categories: InventoryCategory[];
		onAdjust: (ing: Ingredient) => void;
		onEdit: (ing: Ingredient) => void;
		onDelete: (id: number) => void;
	}

	let { ingredients, categories, onAdjust, onEdit, onDelete } = $props<Props>();
</script>

<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-6">
	{#each ingredients as ing}
		<div class="bg-base-100 p-6 rounded-3xl border border-base-200 shadow-sm hover:shadow-md hover:-translate-y-1 transition-all duration-300 group flex flex-col gap-5 min-h-[200px]">
			<div class="flex justify-between items-start">
				<div class="flex flex-col min-w-0">
					<h3 class="font-black text-xl tracking-tight truncate leading-tight mb-1">{ing.name}</h3>
					<div class="flex items-center gap-1.5 flex-wrap">
						<span class="badge badge-ghost badge-xs font-black text-[9px] uppercase tracking-wider border-none bg-base-200">
							{categories.find(c => c.id === ing.category_id)?.name || ing.category}
						</span>
						<span class="text-[10px] opacity-20">•</span>
						<span class="text-[10px] uppercase font-black opacity-40 tracking-widest bg-base-200/50 px-2 py-0.5 rounded">
							{MEASURE_TYPES.find(t => t.id === ing.measure_type)?.icon} {ing.unit}
						</span>
					</div>
				</div>
				<div class="flex gap-2 shrink-0">
					{#if can.manageInventory()}
						<Button 
							variant="ghost" 
							square 
							size="sm" 
							class="bg-base-200 hover:bg-base-300 transition-all rounded-xl"
							onclick={() => onAdjust(ing)} 
							title="Movimientos (Entradas/Salidas)"
						>
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-4 h-4">
								<path stroke-linecap="round" stroke-linejoin="round" d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
							</svg>
						</Button>
					{/if}
					<Button 
						variant="ghost" 
						square 
						size="sm" 
						class="bg-base-200 hover:bg-base-300 transition-colors rounded-xl"
						onclick={() => onEdit(ing)} 
						title="Editar"
					>
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-4 h-4">
							<path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
						</svg>
					</Button>
					<Button 
						variant="ghost" 
						square 
						size="sm" 
						class="bg-base-200 hover:bg-error hover:text-white transition-all rounded-xl"
						onclick={() => ing.id && onDelete(ing.id)} 
						title="Eliminar"
					>
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-4 h-4">
							<path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
						</svg>
					</Button>
				</div>
			</div>
			
			<div class="flex items-end justify-between mt-auto pt-4 border-t border-base-100/50">
				<div class="flex flex-col">
					<span class="text-3xl font-black tracking-tight {ing.current_stock <= ing.minimum_stock ? 'text-error' : 'text-primary'}">
						{ing.current_stock.toFixed(1)} <small class="text-[10px] font-black opacity-40 uppercase ml-1">{ing.unit}</small>
					</span>
					<div class="w-32 h-2 bg-base-200 rounded-full mt-2 overflow-hidden shadow-inner">
						<div 
							class="h-full {ing.current_stock <= ing.minimum_stock ? 'bg-error shadow-[0_0_10px_rgba(255,0,0,0.3)]' : 'bg-primary'} transition-all duration-500" 
							style="width: {Math.min(100, (ing.current_stock / (ing.minimum_stock || 1)) * 50)}%"
						></div>
					</div>
				</div>
				<div class="flex flex-col items-end gap-1">
					{#if ing.current_stock <= ing.minimum_stock}
						<div class="badge badge-error bg-error/15 text-error border-none font-black text-[9px] py-3 px-4 rounded-full animate-pulse uppercase tracking-wider">
							STOCK BAJO
						</div>
					{:else}
						<div class="badge badge-success bg-success/15 text-success border-none font-black text-[9px] py-3 px-4 rounded-full uppercase tracking-wider">
							OK
						</div>
					{/if}
				</div>
			</div>
		</div>
	{/each}
</div>
