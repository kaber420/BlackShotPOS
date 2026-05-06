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

<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
	{#each ingredients as ing}
		<div class="bg-base-100 p-6 rounded-2xl border border-base-200 shadow-sm hover:shadow-md transition-all group overflow-hidden relative">
			<div class="flex justify-between items-start mb-4">
				<div>
					<h3 class="font-black text-lg truncate w-40">{ing.name}</h3>
					<div class="flex items-center gap-1">
						<span class="badge badge-ghost badge-xs font-black text-[8px] uppercase tracking-tighter">
							{categories.find(c => c.id === ing.category_id)?.name || ing.category}
						</span>
						<span class="text-[10px] opacity-40">•</span>
						<span class="text-[10px] uppercase font-bold opacity-40">
							{MEASURE_TYPES.find(t => t.id === ing.measure_type)?.icon} {ing.unit}
						</span>
					</div>
				</div>
				<div class="flex gap-1">
					{#if can.manageInventory()}
						<Button variant="ghost" square size="xs" onclick={() => onAdjust(ing)} title="Movimientos" class="text-warning">📊</Button>
					{/if}
					<Button variant="ghost" square size="xs" onclick={() => onEdit(ing)} title="Editar">✎</Button>
					<Button variant="danger" square size="xs" onclick={() => ing.id && onDelete(ing.id)} title="Eliminar">×</Button>
				</div>
			</div>
			
			<div class="flex items-end justify-between">
				<div class="flex flex-col">
					<span class="text-2xl font-black {ing.current_stock <= ing.minimum_stock ? 'text-error' : 'text-primary'}">
						{ing.current_stock.toFixed(1)} <small class="text-[10px] font-bold opacity-50">{ing.unit}</small>
					</span>
					<div class="w-24 h-1.5 bg-base-200 rounded-full mt-1 overflow-hidden">
						<div 
							class="h-full {ing.current_stock <= ing.minimum_stock ? 'bg-error' : 'bg-primary'} transition-all" 
							style="width: {Math.min(100, (ing.current_stock / (ing.minimum_stock || 1)) * 50)}%"
						></div>
					</div>
				</div>
				<div class="flex flex-col items-end gap-1">
					{#if ing.current_stock <= ing.minimum_stock}
						<div class="badge badge-error badge-xs font-bold animate-bounce text-[8px] p-2">STOCK BAJO</div>
					{/if}
				</div>
			</div>
		</div>
	{/each}
</div>
