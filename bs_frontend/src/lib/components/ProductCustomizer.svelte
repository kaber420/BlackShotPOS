<script lang="ts">
	import { fetchApi } from '$lib/api';
	import { onMount } from 'svelte';
	import type { Product, ProductVariant } from '$lib/api/products';

	let { product, isOpen, onConfirm, onClose } = $props<{
		product: Product;
		isOpen: boolean;
		onConfirm: (modifiers: any[], variant?: ProductVariant) => void;
		onClose: () => void;
	}>();

	let selectedVariant = $state<ProductVariant | null>(null);
	let selectedModifiers = $state<any[]>([]);
	let presets = $state<any[]>([]);
	let showSavePreset = $state(false);
	let presetName = $state('');

	// Agrupar modificadores por su grupo
	let modifierGroups = $derived(product?.modifier_groups || []);
	let variants = $derived(product?.variants || []);

	onMount(async () => {
		if (product?.id) {
			presets = await fetchApi(`/api/v1/pos/products/${product.id}/presets`);
		}
		// Si solo hay una variante, seleccionarla por defecto
		if (variants.length === 1) {
			selectedVariant = variants[0];
		}
	});

	function toggleModifier(mod: any, group: any) {
		if (group.max_selection === 1) {
			selectedModifiers = selectedModifiers.filter(m => m.modifier_group_id !== group.id);
			selectedModifiers.push(mod);
		} else {
			const index = selectedModifiers.findIndex(m => m.id === mod.id);
			if (index >= 0) {
				selectedModifiers.splice(index, 1);
			} else {
				const inGroup = selectedModifiers.filter(m => m.modifier_group_id === group.id).length;
				if (inGroup < group.max_selection) {
					selectedModifiers.push(mod);
				}
			}
		}
	}

	function isSelected(modId: number) {
		return selectedModifiers.some(m => m.id === modId);
	}

	let currentPrice = $derived(() => {
		const base = selectedVariant ? selectedVariant.price : (product?.price || 0);
		const extras = selectedModifiers.reduce((acc, m) => acc + (m.extra_price || 0), 0);
		return base + extras;
	});

	let currentImage = $derived(selectedVariant?.image_url || product?.image_url);

	// Información nutricional combinada (base + variante)
	let nutrition = $derived({
		protein: (selectedVariant?.protein || product?.protein || 0),
		calories: (selectedVariant?.calories || product?.calories || 0),
		carbs: (selectedVariant?.carbs || product?.carbs || 0),
		fats: (selectedVariant?.fats || product?.fats || 0)
	});

	async function saveCurrentAsPreset() {
		if (!presetName) return;
		const modIds = selectedModifiers.map(m => m.id);
		const newPreset = await fetchApi(`/api/v1/pos/products/${product.id}/presets`, {
			method: 'POST',
			body: JSON.stringify({ name: presetName, modifier_ids: modIds })
		});
		presets = [...presets, newPreset];
		showSavePreset = false;
		presetName = '';
	}

	function applyPreset(preset: any) {
		const modIds = JSON.parse(preset.modifier_ids_json);
		const newSelection: any[] = [];
		modifierGroups.forEach((group: any) => {
			group.modifiers.forEach((mod: any) => {
				if (modIds.includes(mod.id)) {
					newSelection.push(mod);
				}
			});
		});
		selectedModifiers = newSelection;
	}

	function handleConfirm() {
		if (variants.length > 0 && !selectedVariant) {
			alert("Por favor selecciona un tamaño.");
			return;
		}
		onConfirm(selectedModifiers, selectedVariant || undefined);
	}
</script>

{#if isOpen}
	<div class="modal modal-open">
		<div class="modal-box max-w-3xl p-0 overflow-hidden bg-base-100 border border-base-300 shadow-2xl">
			<!-- Header with Dynamic Image -->
			<div class="relative h-64 w-full bg-base-200 overflow-hidden">
				{#if currentImage}
					<img src={currentImage} alt={product.name} class="w-full h-full object-cover animate-in fade-in duration-500" />
				{:else}
					<div class="flex items-center justify-center h-full text-base-content/20">
						<svg xmlns="http://www.w3.org/2000/svg" class="h-24 w-24" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
						</svg>
					</div>
				{/if}
				<div class="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-black/80 via-black/40 to-transparent text-white">
					<h2 class="text-3xl font-black uppercase tracking-tighter">{product?.name}</h2>
					<p class="text-sm opacity-90 max-w-lg line-clamp-2">{product?.description || 'Personaliza tu pedido a tu gusto.'}</p>
				</div>
				<button class="btn btn-circle btn-sm absolute top-4 right-4 bg-black/20 border-none text-white hover:bg-black/40" onclick={onClose}>✕</button>
			</div>

			<div class="p-8 overflow-y-auto max-h-[55vh] grid grid-cols-1 md:grid-cols-5 gap-8">
				
				<!-- Left Column: Options (3/5) -->
				<div class="md:col-span-3 flex flex-col gap-8">
					
					<!-- Variants / Sizes Selection -->
					{#if variants.length > 0}
						<div class="animate-in fade-in slide-in-from-left-4">
							<h3 class="text-xs font-black uppercase tracking-widest opacity-50 mb-4 flex items-center gap-2">
								<span class="w-2 h-2 rounded-full bg-primary"></span>
								Selecciona el Tamaño
							</h3>
							<div class="flex flex-wrap gap-3">
								{#each variants as v}
									<button 
										class="btn btn-lg h-auto py-4 px-6 flex flex-col gap-1 items-center {selectedVariant?.id === v.id ? 'btn-primary shadow-lg shadow-primary/20 scale-105' : 'btn-outline border-base-300'}"
										onclick={() => selectedVariant = v}
									>
										<span class="text-lg font-bold uppercase">{v.measure?.name}</span>
										<span class="text-[10px] opacity-70">+{v.measure?.value}{v.measure?.unit}</span>
									</button>
								{/each}
							</div>
						</div>
					{/if}

					<!-- Modifier Groups -->
					{#each modifierGroups as group}
						<div class="animate-in fade-in slide-in-from-left-4">
							<div class="flex justify-between items-end mb-4 border-b border-base-200 pb-2">
								<h3 class="font-black text-xs uppercase tracking-widest opacity-50 flex items-center gap-2">
									<span class="w-2 h-2 rounded-full bg-secondary"></span>
									{group.name}
								</h3>
								<span class="text-[10px] font-bold opacity-40 uppercase">
									{group.is_required ? 'Obligatorio' : 'Opcional'} • Max {group.max_selection}
								</span>
							</div>
							<div class="grid grid-cols-2 gap-3">
								{#each group.modifiers as mod}
									<button 
										class="btn btn-outline h-auto py-4 px-4 justify-between font-bold border-base-300 {isSelected(mod.id) ? 'btn-secondary bg-secondary/10 border-secondary scale-[1.02]' : ''}"
										onclick={() => toggleModifier(mod, group)}
									>
										<span class="text-sm uppercase">{mod.name}</span>
										{#if mod.extra_price > 0}
											<span class="badge badge-sm bg-base-200 border-none font-mono">+${mod.extra_price}</span>
										{/if}
									</button>
								{/each}
							</div>
						</div>
					{/each}
				</div>

				<!-- Right Column: Info & Summary (2/5) -->
				<div class="md:col-span-2 flex flex-col gap-6">
					
					<!-- Nutritional Info Card -->
					{#if nutrition.calories > 0}
						<div class="bg-base-200/50 rounded-2xl p-6 border border-base-300 animate-in fade-in slide-in-from-right-4">
							<h3 class="text-[10px] font-black uppercase tracking-widest opacity-40 mb-4 italic">Información Nutricional Est.</h3>
							<div class="grid grid-cols-2 gap-4">
								<div class="flex flex-col">
									<span class="text-2xl font-black font-mono text-orange-500 leading-none">{nutrition.calories}</span>
									<span class="text-[9px] uppercase font-bold opacity-60">Calorías</span>
								</div>
								<div class="flex flex-col">
									<span class="text-2xl font-black font-mono text-primary leading-none">{nutrition.protein}g</span>
									<span class="text-[9px] uppercase font-bold opacity-60">Proteína</span>
								</div>
								<div class="flex flex-col">
									<span class="text-xl font-black font-mono text-blue-500 leading-none">{nutrition.carbs}g</span>
									<span class="text-[9px] uppercase font-bold opacity-60">Carbos</span>
								</div>
								<div class="flex flex-col">
									<span class="text-xl font-black font-mono text-emerald-500 leading-none">{nutrition.fats}g</span>
									<span class="text-[9px] uppercase font-bold opacity-60">Grasas</span>
								</div>
							</div>
						</div>
					{/if}

					<!-- Presets -->
					{#if presets.length > 0}
						<div class="animate-in fade-in slide-in-from-right-4">
							<h3 class="text-[10px] font-black uppercase tracking-widest opacity-40 mb-3">Tus Favoritos</h3>
							<div class="flex flex-col gap-2">
								{#each presets as preset}
									<button class="btn btn-outline btn-sm btn-accent justify-between font-bold" onclick={() => applyPreset(preset)}>
										{preset.name}
										<span>✨</span>
									</button>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			</div>

			<!-- Footer -->
			<div class="p-8 bg-base-200/80 flex flex-col gap-6 border-t border-base-300">
				{#if showSavePreset}
					<div class="flex gap-2 animate-in slide-in-from-bottom-4">
						<input type="text" placeholder="Nombre favorito (ej: Mid Vainilla)" class="input input-bordered flex-1 font-bold" bind:value={presetName} />
						<button class="btn btn-success px-6 font-bold" onclick={saveCurrentAsPreset}>Guardar</button>
						<button class="btn btn-ghost" onclick={() => showSavePreset = false}>×</button>
					</div>
				{:else}
					<div class="flex justify-between items-center">
						<button class="btn btn-ghost btn-sm text-[10px] font-black uppercase tracking-widest" onclick={() => showSavePreset = true}>
							<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
							</svg>
							Guardar Favorito
						</button>
						<div class="text-right">
							<span class="text-[10px] block opacity-40 uppercase font-black tracking-widest mb-1">Precio Final</span>
							<span class="text-4xl font-black text-primary font-mono">${currentPrice().toFixed(2)}</span>
						</div>
					</div>
				{/if}

				<div class="flex gap-4">
					<button class="btn btn-ghost flex-1 font-bold uppercase" onclick={onClose}>Cancelar</button>
					<button 
						class="btn btn-primary flex-[2] btn-lg shadow-xl shadow-primary/30 font-black uppercase tracking-widest" 
						onclick={handleConfirm}
						disabled={variants.length > 0 && !selectedVariant}
					>
						Añadir al Carrito
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}
