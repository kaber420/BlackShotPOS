<script lang="ts">
	import { type Ingredient, type InventoryCategory } from '$lib/api/ingredients';
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

<div class="bg-base-100 rounded-2xl border border-base-200 overflow-hidden shadow-sm">
	<table class="table table-md w-full">
		<thead class="bg-base-200/50">
			<tr class="border-b border-base-200 text-[10px] font-black uppercase tracking-widest opacity-40">
				<th class="pl-6">Material</th>
				<th>Categoría</th>
				<th>Stock Actual</th>
				<th>Estado</th>
				<th class="text-right pr-6">Acciones</th>
			</tr>
		</thead>
		<tbody>
			{#each ingredients as ing}
				<tr class="hover:bg-base-200/30 transition-colors border-b border-base-100">
					<td class="pl-6 py-4">
						<div class="flex flex-col">
							<span class="font-black text-sm">{ing.name}</span>
							<span class="text-[10px] opacity-40 uppercase font-bold">{ing.measure_type} • {ing.unit}</span>
						</div>
					</td>
					<td>
						<span class="badge badge-ghost badge-sm font-black text-[9px] uppercase">
							{categories.find(c => c.id === ing.category_id)?.name || ing.category}
						</span>
					</td>
					<td>
						<span class="font-black {ing.current_stock <= ing.minimum_stock ? 'text-error' : 'text-primary'}">
							{ing.current_stock.toFixed(1)} <small class="text-[10px] opacity-50">{ing.unit}</small>
						</span>
					</td>
					<td>
						{#if ing.current_stock <= ing.minimum_stock}
							<div class="badge badge-error badge-outline badge-xs font-bold text-[8px] p-2">CRÍTICO</div>
						{:else}
							<div class="badge badge-success badge-outline badge-xs font-bold text-[8px] p-2">OK</div>
						{/if}
					</td>
					<td class="text-right pr-6">
						<div class="flex justify-end gap-1">
							<Button variant="ghost" square size="xs" onclick={() => onAdjust(ing)} title="Movimientos">📊</Button>
							<Button variant="ghost" square size="xs" onclick={() => onEdit(ing)} title="Editar">✎</Button>
							<Button variant="danger" square size="xs" onclick={() => ing.id && onDelete(ing.id)} title="Eliminar">×</Button>
						</div>
					</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>
