<script lang="ts">
	import { ProductService, type Modifier } from '$lib/api/products';
	import { type Ingredient } from '$lib/api/ingredients';
	import { UNIT_OPTIONS } from '$lib/constants/inventory';
	import Button from '$lib/components/ui/Button.svelte';

	interface Props {
		isOpen: boolean;
		groupId: number | null;
		ingredients: Ingredient[];
		onClose: () => void;
		onSave: () => void;
	}

	let { isOpen, groupId, ingredients, onClose, onSave } = $props<Props>();

	let modifierForm = $state<Partial<Modifier>>({ 
		name: '', 
		extra_price: 0, 
		ingredient_id: undefined, 
		input_quantity: 0, 
		input_unit: 'ml' 
	});

	let isSubmitting = $state(false);
	let showAdvancedModifier = $state(false);

	$effect(() => {
		if (isOpen && groupId) {
			showAdvancedModifier = false;
			const firstIng = ingredients[0];
			modifierForm = { 
				name: '', 
				extra_price: 0, 
				ingredient_id: firstIng?.id, 
				input_quantity: 0, 
				input_unit: firstIng ? (UNIT_OPTIONS as any)[firstIng.measure_type][0].id : 'ml' 
			};
			const modal = document.getElementById('modal_modificador') as HTMLDialogElement;
			if (modal && !modal.open) modal.showModal();
		} else if (!isOpen) {
			const modal = document.getElementById('modal_modificador') as HTMLDialogElement;
			if (modal && modal.open) modal.close();
		}
	});

	async function handleSubmit(e: Event) {
		e.preventDefault();
		if (!groupId) return;
		try {
			isSubmitting = true;
			await ProductService.createModifier({
				...modifierForm,
				modifier_group_id: groupId
			} as any);
			onSave();
			onClose();
		} catch (e: any) {
			alert('Error: ' + e.message);
		} finally {
			isSubmitting = false;
		}
	}

	const selectedIngredient = $derived(ingredients.find(i => i.id === modifierForm.ingredient_id));
</script>

<dialog id="modal_modificador" class="modal">
	<div class="modal-box rounded-3xl p-8">
		<h3 class="font-black text-2xl mb-6 tracking-tighter">Añadir Opción</h3>
		<form onsubmit={handleSubmit} class="space-y-4">
			<div class="form-control">
				<label class="label p-0 mb-1" for="m_name"><span class="label-text text-[10px] uppercase font-black opacity-40">Nombre de la Opción (ej. Soya)</span></label>
				<input type="text" id="m_name" bind:value={modifierForm.name} class="input input-bordered rounded-xl font-bold" required />
			</div>
			<div class="form-control">
				<label class="label p-0 mb-1" for="m_ing"><span class="label-text text-[10px] uppercase font-black opacity-40">Vincular al Inventario (Insumo)</span></label>
				<select 
					bind:value={modifierForm.ingredient_id} 
					class="select select-bordered rounded-xl font-bold"
					onchange={() => {
						if (selectedIngredient) modifierForm.input_unit = selectedIngredient.unit;
					}}
				>
					<option value={undefined}>No descontar inventario</option>
					{#each ingredients as ing}<option value={ing.id}>{ing.name}</option>{/each}
				</select>
			</div>

			<div class="form-control">
				<label class="label p-0 mb-1" for="m_price"><span class="label-text text-[10px] uppercase font-black opacity-40">Precio Extra ($)</span></label>
				<input type="number" bind:value={modifierForm.extra_price} class="input input-bordered rounded-xl font-bold" />
			</div>

			<div class="py-2">
				<button 
					type="button" 
					class="text-[10px] uppercase font-black opacity-40 hover:opacity-100 flex items-center gap-1 transition-all"
					onclick={() => showAdvancedModifier = !showAdvancedModifier}
				>
					{showAdvancedModifier ? '▾ Ocultar' : '▸'} Configuración de Descuento Fijo (Opcional)
				</button>
				
				{#if showAdvancedModifier}
					<div class="grid grid-cols-2 gap-4 mt-3 p-4 bg-base-200/50 rounded-2xl animate-in fade-in slide-in-from-top-2">
						<div class="form-control">
							<label class="label p-0 mb-1" for="m_qty"><span class="label-text text-[9px] uppercase font-bold opacity-60">Cantidad Fija</span></label>
							<input type="number" step="0.01" bind:value={modifierForm.input_quantity} class="input input-bordered input-sm rounded-xl font-bold" />
						</div>
						<div class="form-control">
							<label class="label p-0 mb-1" for="m_unit"><span class="label-text text-[9px] uppercase font-bold opacity-60">Unidad</span></label>
							<select 
								bind:value={modifierForm.input_unit} 
								class="select select-bordered select-sm rounded-xl font-bold"
							>
								{#if selectedIngredient}
									{#each (UNIT_OPTIONS as any)[selectedIngredient.measure_type] as u}
										<option value={u.id}>{u.name}</option>
									{/each}
								{:else}
									<option value="ml">ml</option>
								{/if}
							</select>
						</div>
						<p class="col-span-2 text-[9px] opacity-50 italic">
							* Usa esto solo si la cantidad es SIEMPRE la misma. Si depende de la receta (Chico/Grande), déjalo en 0.
						</p>
					</div>
				{/if}
			</div>

			<div class="modal-action">
				<Button type="submit" variant="secondary" class="px-10" isLoading={isSubmitting}>Guardar Opción</Button>
			</div>
		</form>
	</div>
	<form method="dialog" class="modal-backdrop bg-black/40" onsubmit={(e) => { e.preventDefault(); onClose(); }}><button onclick={onClose}>close</button></form>
</dialog>
