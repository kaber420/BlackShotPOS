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
    import Button from '$lib/components/ui/Button.svelte';

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

	let currentImage = $derived(selectedVariant?.image_url || product?.image_url || '');

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
	<div class="modal modal-open backdrop-blur-md transition-all duration-300 ease-out z-[100]">
		<div class="modal-box max-w-2xl p-0 overflow-hidden bg-base-100 border border-base-200 shadow-[0_32px_64px_-12px_rgba(0,0,0,0.3)] rounded-[2.5rem] animate-in zoom-in-95 duration-200">
            
            <!-- Hero Header (Panoramic) -->
            <div class="relative h-56 w-full bg-base-300 overflow-hidden">
                {#if currentImage}
                    <img src={currentImage} alt={product.name} class="w-full h-full object-cover animate-in fade-in duration-700" />
                {:else}
                    <div class="w-full h-full flex items-center justify-center bg-gradient-to-br from-primary/10 to-primary/20">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-20 w-20 text-primary/20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                    </div>
                {/if}
                
                <!-- Title Overlay -->
                <div class="absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-transparent flex flex-col justify-end p-8">
                    <h2 class="text-4xl font-black text-white uppercase tracking-tighter drop-shadow-lg leading-tight line-clamp-1">
                        {product?.name}
                    </h2>
                    <p class="text-white/70 text-xs font-bold uppercase tracking-widest mt-1 opacity-80">
                        Personaliza tu elección
                    </p>
                </div>

                <!-- Close Button -->
                <button 
                    class="absolute top-6 right-6 w-10 h-10 bg-black/20 hover:bg-black/40 backdrop-blur-xl rounded-full text-white flex items-center justify-center transition-all border border-white/10 group active:scale-90"
                    onclick={onClose}
                    aria-label="Cerrar"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="3" stroke="currentColor" class="w-4 h-4 group-hover:rotate-90 transition-transform"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                </button>
            </div>

            <!-- Scrollable Options Area -->
            <div class="p-8 flex flex-col gap-8 max-h-[55vh] overflow-y-auto elegant-scroll">
                
                <!-- Size Selection (Horizontal Price Chips) -->
                {#if variants.length > 0}
                    <div class="animate-in fade-in slide-in-from-bottom-4 duration-500">
                        <h3 class="text-[10px] font-black uppercase tracking-[0.2em] opacity-40 mb-4 px-1 flex items-center gap-2">
                            <span class="w-1.5 h-1.5 rounded-full bg-primary animate-pulse"></span>
                            Tamaño del Producto
                        </h3>
                        <div class="flex flex-wrap gap-2.5">
                            {#each variants as v}
                                <button 
                                    class="flex items-center gap-3 px-6 py-4 rounded-2xl border-2 transition-all duration-300 font-black
                                    {selectedVariant?.id === v.id 
                                        ? 'bg-primary border-primary text-white scale-105 shadow-xl shadow-primary/20' 
                                        : 'bg-base-200/50 border-transparent text-base-content/70 hover:bg-base-200'}"
                                    onclick={() => selectedVariant = v}
                                >
                                    <span class="uppercase text-sm tracking-tight">{v.measure?.name}</span>
                                    <span class="text-xs font-mono opacity-60 bg-black/5 px-2 py-0.5 rounded-lg">${v.price.toFixed(0)}</span>
                                </button>
                            {/each}
                        </div>
                    </div>
                {/if}

                <!-- Modifiers (Modern Two-Column Grid) -->
                {#each modifierGroups as group}
                    <div class="animate-in fade-in slide-in-from-bottom-4 duration-500 delay-100">
                        <div class="flex justify-between items-end mb-4 px-1 border-b border-base-200 pb-2">
                            <h3 class="text-[10px] font-black uppercase tracking-[0.2em] opacity-40">{group.name}</h3>
                            <span class="text-[9px] font-bold opacity-30 uppercase tracking-tighter">
                                {group.is_required ? 'Obligatorio' : 'Opcional'} • Máx {group.max_selection}
                            </span>
                        </div>
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                            {#each group.modifiers as mod}
                                <button 
                                    class="flex items-center justify-between px-5 py-4 rounded-2xl border-2 transition-all duration-300 font-bold group/mod
                                    {isSelected(mod.id) 
                                        ? 'bg-secondary/10 border-secondary text-secondary shadow-lg shadow-secondary/5' 
                                        : 'bg-base-200/50 border-transparent text-base-content/70 hover:bg-base-200 hover:border-base-300'}"
                                    onclick={() => toggleModifier(mod, group)}
                                >
                                    <div class="flex items-center gap-3">
                                        <div class="w-4 h-4 rounded-full border-2 border-current flex items-center justify-center transition-all {isSelected(mod.id) ? 'bg-secondary' : 'bg-transparent'}">
                                            {#if isSelected(mod.id)}
                                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="4" stroke="white" class="w-2.5 h-2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>
                                            {/if}
                                        </div>
                                        <span class="uppercase text-[11px] tracking-tight">{mod.name}</span>
                                    </div>
                                    {#if mod.extra_price > 0}
                                        <span class="text-[10px] font-mono opacity-50 bg-black/5 px-2 py-0.5 rounded-lg">
                                            +${mod.extra_price.toFixed(0)}
                                        </span>
                                    {/if}
                                </button>
                            {/each}
                        </div>
                    </div>
                {/each}

                <!-- Special Instructions Field -->
                <div class="animate-in fade-in slide-in-from-bottom-4 duration-500 delay-200 pb-4">
                    <h3 class="text-[10px] font-black uppercase tracking-[0.2em] opacity-40 mb-4 px-1 flex items-center gap-2">
                         <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-3.5 h-3.5"><path stroke-linecap="round" stroke-linejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" /></svg>
                        Instrucciones Especiales
                    </h3>
                    <textarea 
                        placeholder="Ej: Sin popote, extra caliente, sin hielo..."
                        class="textarea textarea-bordered w-full rounded-3xl bg-base-200/50 border-transparent focus:border-primary/30 focus:bg-base-100 transition-all font-bold text-sm h-28 elegant-scroll p-6 shadow-inner"
                        bind:value={presetName}
                    ></textarea>
                </div>
            </div>

            <!-- Fixed Footer with Integrated Totalizer -->
            <div class="p-8 bg-base-100 border-t border-base-200 flex items-center gap-4">
                <button 
                    class="flex-1 bg-primary hover:bg-primary/90 text-white rounded-[1.8rem] py-5 px-8 font-black uppercase tracking-[0.1em] text-lg shadow-2xl shadow-primary/30 transition-all active:scale-[0.97] disabled:opacity-50 disabled:grayscale flex items-center justify-center gap-3 group"
                    onclick={handleConfirm}
                    disabled={variants.length > 0 && !selectedVariant}
                >
                    <span>Añadir al Pedido</span>
                    <span class="w-1.5 h-1.5 rounded-full bg-white/40 group-hover:scale-150 transition-transform"></span>
                    <span class="font-mono text-2xl tracking-tighter">${currentPrice().toFixed(2)}</span>
                </button>
            </div>
        </div>
	</div>
{/if}

<style>
    .elegant-scroll::-webkit-scrollbar {
        width: 4px;
    }
    .elegant-scroll::-webkit-scrollbar-thumb {
        background: rgba(0,0,0,0.1);
        border-radius: 10px;
    }
    .elegant-scroll::-webkit-scrollbar-track {
        background: transparent;
    }
</style>


