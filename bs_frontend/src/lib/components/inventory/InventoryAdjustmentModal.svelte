<script lang="ts">
	import { IngredientService, type Ingredient, type InventoryAdjustmentCreate, AdjustmentReason } from '$lib/api/ingredients';
	import { REASON_LABELS } from '$lib/constants/inventory';
	import Button from '$lib/components/ui/Button.svelte';

	interface Props {
		isOpen: boolean;
		ingredient: Ingredient | null;
		initialType?: 'IN' | 'OUT' | 'SET';
		onClose: () => void;
		onSave: () => void;
	}

	let { isOpen, ingredient, initialType = 'OUT', onClose, onSave } = $props<Props>();

	let movementType = $state<'IN' | 'OUT' | 'SET'>(initialType);
	let isSubmitting = $state(false);

	let adjustmentForm = $state<InventoryAdjustmentCreate>({
		ingredient_id: 0,
		quantity: 0,
		reason: AdjustmentReason.WASTE,
		note: ''
	});

	$effect(() => {
		if (isOpen && ingredient) {
			movementType = initialType;
			let defaultReason = AdjustmentReason.WASTE;
			if (movementType === 'IN') defaultReason = AdjustmentReason.PURCHASE;
			if (movementType === 'SET') defaultReason = AdjustmentReason.PHYSICAL_COUNT;

			adjustmentForm = {
				ingredient_id: ingredient.id!,
				quantity: 0,
				reason: defaultReason,
				note: '',
				expiration_date: ''
			};
			const modal = document.getElementById('modal_merma') as HTMLDialogElement;
			if (modal && !modal.open) modal.showModal();
		} else if (!isOpen) {
			const modal = document.getElementById('modal_merma') as HTMLDialogElement;
			if (modal && modal.open) modal.close();
		}
	});

	$effect(() => {
		if (movementType === 'IN') adjustmentForm.reason = AdjustmentReason.PURCHASE;
		else if (movementType === 'SET') adjustmentForm.reason = AdjustmentReason.PHYSICAL_COUNT;
		else if (movementType === 'OUT') adjustmentForm.reason = AdjustmentReason.WASTE;
	});

	async function handleSubmit(e: Event) {
		e.preventDefault();
		try {
			isSubmitting = true;
			const payload = { ...adjustmentForm };
			if (!payload.expiration_date) {
				delete payload.expiration_date;
			}
			await IngredientService.registerAdjustment(payload);
			onSave();
			onClose();
		} catch (e: any) {
			alert('Error al registrar movimiento: ' + e.message);
		} finally {
			isSubmitting = false;
		}
	}
</script>

<dialog id="modal_merma" class="modal">
	<div 
		class="modal-box rounded-[2rem] p-8 transition-all duration-500 bg-base-100 border border-white/5"
		style="box-shadow: 0 0 50px -10px {movementType === 'IN' ? 'rgba(34, 197, 94, 0.3)' : movementType === 'SET' ? 'rgba(59, 130, 246, 0.3)' : 'rgba(239, 68, 68, 0.3)'}"
	>
		<div class="flex justify-between items-start mb-8">
			<div>
				<h3 class="font-black text-4xl tracking-tighter bg-clip-text text-transparent bg-gradient-to-r {movementType === 'IN' ? 'from-success to-emerald-400' : movementType === 'SET' ? 'from-primary to-blue-400' : 'from-error to-rose-400'}">
					Movimiento
				</h3>
				<p class="text-[10px] opacity-40 uppercase font-black tracking-[0.2em] mt-1">{ingredient?.name}</p>
			</div>
			<button class="btn btn-sm btn-circle btn-ghost opacity-30 hover:opacity-100 transition-all" onclick={onClose}>✕</button>
		</div>

		<div class="flex p-1.5 bg-base-200/50 rounded-2xl mb-10 gap-1 border border-white/5">
			<button 
				type="button" 
				class="flex-1 py-3 rounded-xl text-xs font-black uppercase tracking-wider transition-all duration-300 {movementType === 'IN' ? 'bg-success text-success-content shadow-[0_0_15px_rgba(34,197,94,0.4)] scale-100' : 'opacity-40 hover:opacity-70 scale-95'}" 
				onclick={() => movementType = 'IN'}
			>
				📥 Entrada
			</button>
			<button 
				type="button" 
				class="flex-1 py-3 rounded-xl text-xs font-black uppercase tracking-wider transition-all duration-300 {movementType === 'OUT' ? 'bg-error text-error-content shadow-[0_0_15px_rgba(239,68,68,0.4)] scale-100' : 'opacity-40 hover:opacity-70 scale-95'}" 
				onclick={() => movementType = 'OUT'}
			>
				📤 Salida
			</button>
			<button 
				type="button" 
				class="flex-1 py-3 rounded-xl text-xs font-black uppercase tracking-wider transition-all duration-300 {movementType === 'SET' ? 'bg-primary text-primary-content shadow-[0_0_15px_rgba(59,130,246,0.4)] scale-100' : 'opacity-40 hover:opacity-70 scale-95'}" 
				onclick={() => movementType = 'SET'}
			>
				⚖️ Conteo
			</button>
		</div>
		
		<form onsubmit={handleSubmit} class="space-y-8">
			<div class="grid grid-cols-1 md:grid-cols-2 gap-8">
				<div class="form-control">
					<label class="label p-0 mb-3" for="adj_qty">
						<span class="label-text text-[10px] uppercase font-black opacity-30 tracking-widest">
							{#if movementType === 'SET'}Cantidad Real
							{:else}Cantidad a {#if movementType === 'IN'}Ingresar{:else}Descontar{/if}{/if} ({ingredient?.unit})
						</span>
					</label>
					<input 
						type="number" 
						step="0.01" 
						id="adj_qty" 
						bind:value={adjustmentForm.quantity} 
						class="input input-lg bg-base-200/50 border-none rounded-[1.5rem] font-black text-3xl h-20 focus:ring-2 {movementType === 'IN' ? 'focus:ring-success/30' : movementType === 'SET' ? 'focus:ring-primary/30' : 'focus:ring-error/30'} transition-all" 
						placeholder="0.00" 
						required 
					/>
				</div>
				<div class="form-control">
					<label class="label p-0 mb-3" for="adj_reason">
						<span class="label-text text-[10px] uppercase font-black opacity-30 tracking-widest">Razón</span>
					</label>
					<select bind:value={adjustmentForm.reason} class="select select-lg bg-base-200/50 border-none rounded-[1.5rem] font-bold h-20 text-lg transition-all">
						{#each Object.entries(REASON_LABELS) as [value, label]}
							{#if movementType === 'IN' && (value === 'PURCHASE' || value === 'RESTOCK')}
								<option {value}>{label}</option>
							{:else if movementType === 'OUT' && ['WASTE', 'EXPIRED', 'ERROR', 'THEFT', 'PERSONAL_CONSUMPTION'].includes(value)}
								<option {value}>{label}</option>
							{:else if movementType === 'SET' && (value === 'PHYSICAL_COUNT' || value === 'CORRECTION')}
								<option {value}>{label}</option>
							{/if}
						{/each}
					</select>
				</div>
			</div>

			{#if movementType === 'IN'}
				<div class="form-control animate-in fade-in slide-in-from-top-2">
					<label class="label p-0 mb-3" for="adj_expiry">
						<span class="label-text text-[10px] uppercase font-black opacity-30 tracking-widest">Fecha de Caducidad (Opcional)</span>
					</label>
					<input 
						type="date" 
						id="adj_expiry" 
						bind:value={adjustmentForm.expiration_date} 
						class="input input-lg bg-base-200/50 border-none rounded-[1.5rem] font-bold h-20 text-lg transition-all"
					/>
				</div>
			{/if}

			{#if movementType === 'SET'}
				<div class="flex gap-4 p-5 rounded-2xl bg-primary/5 border border-primary/10 items-center">
					<div class="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center text-xl shadow-[0_0_15px_rgba(59,130,246,0.3)]">💡</div>
					<p class="text-[11px] font-medium leading-relaxed opacity-70">
						El stock actual (<span class="font-black text-primary">{ingredient?.current_stock}</span>) será reemplazado por el valor ingresado.
					</p>
				</div>
			{/if}

			<div class="form-control">
				<label class="label p-0 mb-3" for="adj_note">
					<span class="label-text text-[10px] uppercase font-black opacity-30 tracking-widest">Notas de Auditoría</span>
				</label>
				<textarea 
					id="adj_note" 
					bind:value={adjustmentForm.note} 
					class="textarea bg-base-200/50 border-none rounded-2xl font-medium h-24 text-sm focus:ring-1 focus:ring-white/10" 
					placeholder="Ej: Factura #123, Lote caducado, ajuste semanal..."
				></textarea>
			</div>

			<div class="modal-action mt-4">
				<Button 
					type="submit" 
					variant="primary" 
					class="btn-lg btn-block rounded-2xl border-none font-black uppercase tracking-[0.2em] shadow-2xl transition-all duration-300 hover:scale-[1.01] active:scale-[0.98] {movementType === 'IN' ? 'bg-success text-success-content shadow-success/20' : movementType === 'SET' ? 'bg-primary text-primary-content shadow-primary/20' : 'bg-error text-error-content shadow-error/20'}" 
					isLoading={isSubmitting}
				>
					Confirmar Registro
				</Button>
			</div>
		</form>
	</div>
	<form method="dialog" class="modal-backdrop bg-black/80 backdrop-blur-md" onsubmit={(e) => { e.preventDefault(); onClose(); }}><button onclick={onClose}>close</button></form>
</dialog>
