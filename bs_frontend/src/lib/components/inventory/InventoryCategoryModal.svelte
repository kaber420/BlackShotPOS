<script lang="ts">
	import { IngredientService, type InventoryCategory } from '$lib/api/ingredients';
	import Button from '$lib/components/ui/Button.svelte';

	interface Props {
		isOpen: boolean;
		categories: InventoryCategory[];
		onClose: () => void;
		onRefresh: () => void;
	}

	let { isOpen, categories, onClose, onRefresh } = $props<Props>();

	let newCategoryName = $state('');
	let isSubmitting = $state(false);

	$effect(() => {
		if (isOpen) {
			const modal = document.getElementById('modal_categorias') as HTMLDialogElement;
			if (modal && !modal.open) modal.showModal();
		} else {
			const modal = document.getElementById('modal_categorias') as HTMLDialogElement;
			if (modal && modal.open) modal.close();
		}
	});

	async function handleCreateCategory() {
		if (!newCategoryName.trim()) return;
		try {
			isSubmitting = true;
			await IngredientService.createCategory({ name: newCategoryName });
			newCategoryName = '';
			onRefresh();
		} catch (e: any) {
			alert('Error: ' + e.message);
		} finally {
			isSubmitting = false;
		}
	}

	async function handleDeleteCategory(id: number) {
		if (!confirm('¿Eliminar esta categoría? Los insumos vinculados no se eliminarán pero perderán la categoría.')) return;
		try {
			await IngredientService.deleteCategory(id);
			onRefresh();
		} catch (e: any) {
			alert('Error: ' + e.message);
		}
	}
</script>

<dialog id="modal_categorias" class="modal">
	<div class="modal-box rounded-3xl p-8 max-w-md">
		<h3 class="font-black text-2xl mb-6 tracking-tighter">Gestionar Categorías</h3>
		<div class="flex gap-2 mb-6">
			<input 
				type="text" 
				bind:value={newCategoryName} 
				placeholder="Nueva categoría..." 
				class="input input-bordered w-full rounded-xl font-bold"
				onkeydown={(e) => e.key === 'Enter' && handleCreateCategory()}
			/>
			<Button variant="primary" onclick={handleCreateCategory} isLoading={isSubmitting}>Añadir</Button>
		</div>
		
		<div class="space-y-2 max-h-80 overflow-y-auto pr-2">
			{#each categories as cat}
				<div class="flex items-center justify-between p-4 bg-base-200/50 rounded-2xl group transition-all hover:bg-base-200">
					<span class="font-bold text-sm">{cat.name}</span>
					<button 
						class="btn btn-ghost btn-circle btn-xs text-error opacity-40 group-hover:opacity-100 transition-all" 
						onclick={() => cat.id && handleDeleteCategory(cat.id)}
						title="Eliminar categoría"
					>✕</button>
				</div>
			{:else}
				<div class="flex flex-col items-center justify-center py-10 opacity-30">
					<span class="text-4xl mb-2">📂</span>
					<p class="text-xs italic font-bold uppercase tracking-widest">No hay categorías</p>
				</div>
			{/each}
		</div>
	</div>
	<form method="dialog" class="modal-backdrop bg-black/60 backdrop-blur-sm" onsubmit={(e) => { e.preventDefault(); onClose(); }}><button onclick={onClose}>close</button></form>
</dialog>
