<script lang="ts">
	import { ProductService, type ModifierGroup } from '$lib/api/products';
	import Button from '$lib/components/ui/Button.svelte';

	interface Props {
		isOpen: boolean;
		group?: Partial<ModifierGroup> | null;
		onClose: () => void;
		onSave: (group: ModifierGroup) => void;
	}

	let { isOpen, group, onClose, onSave } = $props<Props>();

	let groupForm = $state<Partial<ModifierGroup>>({ 
		name: '', 
		min_selection: 0, 
		max_selection: 1, 
		is_required: false 
	});
	let isSubmitting = $state(false);

	$effect(() => {
		if (isOpen) {
			if (group) {
				groupForm = { ...group };
			} else {
				groupForm = { name: '', min_selection: 0, max_selection: 1, is_required: false };
			}
			const modal = document.getElementById('modal_grupo') as HTMLDialogElement;
			if (modal && !modal.open) modal.showModal();
		} else {
			const modal = document.getElementById('modal_grupo') as HTMLDialogElement;
			if (modal && modal.open) modal.close();
		}
	});

	async function handleSubmit(e: Event) {
		e.preventDefault();
		try {
			isSubmitting = true;
			const result = await ProductService.createModifierGroup(groupForm);
			onSave(result);
			onClose();
		} catch (e: any) {
			alert('Error: ' + e.message);
		} finally {
			isSubmitting = false;
		}
	}
</script>

<dialog id="modal_grupo" class="modal">
	<div class="modal-box rounded-3xl p-8">
		<h3 class="font-black text-2xl mb-6 tracking-tighter">
			{group?.id ? 'Editar Grupo' : 'Nuevo Grupo'}
		</h3>
		<form onsubmit={handleSubmit} class="space-y-4">
			<div class="form-control">
				<label class="label p-0 mb-1" for="g_name"><span class="label-text text-[10px] uppercase font-black opacity-40">Nombre del Grupo (ej. Mis Leches)</span></label>
				<input type="text" id="g_name" bind:value={groupForm.name} class="input input-bordered focus:input-secondary rounded-xl font-bold" required />
			</div>
			<div class="modal-action">
				<Button type="submit" variant="secondary" class="px-10" isLoading={isSubmitting}>
					{group?.id ? 'Guardar Cambios' : 'Crear Grupo'}
				</Button>
			</div>
		</form>
	</div>
	<form method="dialog" class="modal-backdrop bg-black/40" onsubmit={(e) => { e.preventDefault(); onClose(); }}><button onclick={onClose}>close</button></form>
</dialog>
