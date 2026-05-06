<script lang="ts">
	import { IngredientService, type Ingredient, type InventoryCategory } from '$lib/api/ingredients';
	import { MEASURE_TYPES, UNIT_OPTIONS } from '$lib/constants/inventory';
	import Button from '$lib/components/ui/Button.svelte';

	interface Props {
		isOpen: boolean;
		ingredient?: Ingredient | null;
		categories: InventoryCategory[];
		onClose: () => void;
		onSave: (ingredient: Ingredient) => void;
	}

	let { isOpen, ingredient, categories, onClose, onSave } = $props<Props>();

	let ingredientForm = $state<Partial<Ingredient>>({ 
		name: '', 
		measure_type: 'weight', 
		unit: 'g', 
		current_stock: 0, 
		minimum_stock: 0,
		category_id: undefined
	});

	let isSubmitting = $state(false);

	$effect(() => {
		if (isOpen) {
			if (ingredient) {
				ingredientForm = { ...ingredient };
			} else {
				ingredientForm = { 
					name: '', 
					measure_type: 'weight', 
					unit: 'g', 
					current_stock: 0, 
					minimum_stock: 0,
					category_id: categories[0]?.id
				};
			}
			const modal = document.getElementById('modal_ingrediente') as HTMLDialogElement;
			if (modal && !modal.open) modal.showModal();
		} else {
			const modal = document.getElementById('modal_ingrediente') as HTMLDialogElement;
			if (modal && modal.open) modal.close();
		}
	});

	async function handleSubmit(e: Event) {
		e.preventDefault();
		try {
			isSubmitting = true;
			let result: Ingredient;
			if (ingredient?.id) {
				result = await IngredientService.update(ingredient.id, ingredientForm);
			} else {
				result = await IngredientService.create(ingredientForm as Ingredient);
			}
			onSave(result);
			onClose();
		} catch (e: any) {
			alert('Error: ' + e.message);
		} finally {
			isSubmitting = false;
		}
	}
</script>

<dialog id="modal_ingrediente" class="modal">
	<div class="modal-box rounded-3xl p-8">
		<h3 class="font-black text-2xl mb-6 tracking-tighter">
			{ingredient?.id ? 'Editar Materia Prima' : 'Nueva Materia Prima'}
		</h3>
		<form onsubmit={handleSubmit} class="space-y-4">
			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				<div class="form-control">
					<label class="label p-0 mb-1" for="ing_name"><span class="label-text text-[10px] uppercase font-black opacity-40">Nombre</span></label>
					<input type="text" id="ing_name" bind:value={ingredientForm.name} class="input input-bordered focus:input-primary rounded-xl font-bold" required />
				</div>
				<div class="form-control">
					<label class="label p-0 mb-1" for="ing_cat"><span class="label-text text-[10px] uppercase font-black opacity-40">Categoría</span></label>
					<select bind:value={ingredientForm.category_id} class="select select-bordered rounded-xl font-bold">
						<option value={undefined}>Sin categoría</option>
						{#each categories as cat}
							<option value={cat.id}>{cat.name}</option>
						{/each}
					</select>
				</div>
			</div>
			<div class="form-control">
				<label class="label p-0 mb-1"><span class="label-text text-[10px] uppercase font-black opacity-40">Naturaleza del Insumo</span></label>
				<div class="grid grid-cols-3 gap-2">
					{#each MEASURE_TYPES as type}
						<button 
							type="button"
							class="flex flex-col items-center p-3 rounded-2xl border-2 transition-all {ingredientForm.measure_type === type.id ? 'border-primary bg-primary/5' : 'border-base-200'}"
							onclick={() => {
								ingredientForm.measure_type = type.id as any;
								ingredientForm.unit = (UNIT_OPTIONS as any)[type.id][0].id;
							}}
						>
							<span class="text-xl">{type.icon}</span>
							<span class="text-[8px] font-black uppercase mt-1">{type.name}</span>
						</button>
					{/each}
				</div>
			</div>

			<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
				<div class="form-control">
					<label class="label p-0 mb-1" for="ing_unit"><span class="label-text text-[10px] uppercase font-black opacity-40">Unidad Base</span></label>
					<select bind:value={ingredientForm.unit} class="select select-bordered rounded-xl font-bold">
						{#each (UNIT_OPTIONS as any)[ingredientForm.measure_type || 'weight'] || [] as u}
							<option value={u.id}>{u.name}</option>
						{/each}
					</select>
				</div>
				<div class="form-control">
					<label class="label p-0 mb-1" for="ing_stock">
                        <span class="label-text text-[10px] uppercase font-black opacity-40">Stock Actual ({ingredientForm.unit})</span>
                    </label>
					<input type="number" step="0.1" bind:value={ingredientForm.current_stock} class="input input-bordered rounded-xl font-bold bg-base-200" readonly title="El stock se ajusta mediante Movimientos" />
				</div>
				<div class="form-control">
					<label class="label p-0 mb-1" for="ing_min_stock">
                        <span class="label-text text-[10px] uppercase font-black opacity-40">Stock Mínimo</span>
                    </label>
					<input type="number" step="0.1" id="ing_min_stock" bind:value={ingredientForm.minimum_stock} class="input input-bordered rounded-xl font-bold border-warning/30" />
				</div>
			</div>
			<div class="modal-action">
				<Button type="submit" variant="primary" class="px-10" isLoading={isSubmitting}>Guardar</Button>
			</div>
		</form>
	</div>
	<form method="dialog" class="modal-backdrop bg-black/40" onsubmit={(e) => { e.preventDefault(); onClose(); }}><button onclick={onClose}>close</button></form>
</dialog>
