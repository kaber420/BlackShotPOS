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
	
	let groupForm = $state({ name: '', min_selection: 0, max_selection: 1, is_required: false });
	let dialogElement = $state<HTMLDialogElement>();
	let isSubmitting = $state(false);

	$effect(() => {
		if (isOpen) {
			if (!group) {
				groupForm = { name: '', min_selection: 0, max_selection: 1, is_required: false };
			} else {
				groupForm = { 
					name: group.name || '', 
					min_selection: group.min_selection || 0, 
					max_selection: group.max_selection || 1, 
					is_required: !!group.is_required 
				};
			}
			dialogElement?.showModal();
		} else {
			dialogElement?.close();
		}
	});

	async function handleSubmit(e: Event) {
		e.preventDefault();
		try {
			isSubmitting = true;
			let result;
			if (group?.id) {
				result = await ProductService.updateModifierGroup(group.id, groupForm);
			} else {
				result = await ProductService.createModifierGroup(groupForm);
			}
			onSave(result);
			onClose();
		} catch (e: any) {
			alert('Error: ' + (e.message || 'Error desconocido'));
		} finally {
			isSubmitting = false;
		}
	}
</script>

<dialog bind:this={dialogElement} id="modal_grupo" class="modal z-[80]">
	<div class="modal-box rounded-3xl p-8 border border-base-content/5 shadow-2xl">
		<h3 class="font-black text-2xl mb-6 tracking-tighter uppercase flex items-center gap-2">
			<span class="w-2 h-6 bg-secondary rounded-full"></span>
			{group?.id ? 'Editar Grupo' : 'Nuevo Grupo'}
		</h3>
		
		<form onsubmit={handleSubmit} class="space-y-6">
			<div class="form-control">
				<label class="label p-0 mb-1" for="g_name"><span class="label-text text-[10px] uppercase font-black opacity-40">Nombre del Grupo</span></label>
				<input type="text" id="g_name" bind:value={groupForm.name} placeholder="Ej. Mis Leches, Extras..." class="input input-bordered focus:input-secondary rounded-xl font-bold" required />
			</div>

			<div class="grid grid-cols-2 gap-4">
				<div class="form-control">
					<label class="label p-0 mb-1" for="g_min"><span class="label-text text-[10px] uppercase font-black opacity-40">Selección Mínima</span></label>
					<input type="number" id="g_min" bind:value={groupForm.min_selection} min="0" class="input input-bordered focus:input-secondary rounded-xl font-bold" />
				</div>
				<div class="form-control">
					<label class="label p-0 mb-1" for="g_max"><span class="label-text text-[10px] uppercase font-black opacity-40">Selección Máxima</span></label>
					<input type="number" id="g_max" bind:value={groupForm.max_selection} min="1" class="input input-bordered focus:input-secondary rounded-xl font-bold" />
				</div>
			</div>

			<div class="bg-base-200/50 p-4 rounded-2xl flex items-center justify-between border border-transparent hover:border-secondary/20 transition-all">
				<div>
					<p class="text-xs font-black uppercase">¿Es obligatorio?</p>
					<p class="text-[9px] opacity-50 font-bold uppercase">El cliente debe elegir al menos una opción</p>
				</div>
				<input type="checkbox" class="toggle toggle-secondary" bind:checked={groupForm.is_required} />
			</div>

			<div class="modal-action pt-4">
				<Button type="submit" variant="secondary" class="w-full rounded-2xl font-black py-6 shadow-lg shadow-secondary/20" isLoading={isSubmitting}>
					{group?.id ? 'Guardar Cambios' : 'Crear Grupo Maestro'}
				</Button>
			</div>
		</form>
	</div>
	<form method="dialog" class="modal-backdrop bg-black/60 backdrop-blur-sm" onsubmit={(e) => { e.preventDefault(); onClose(); }}><button onclick={onClose}>close</button></form>
</dialog>
