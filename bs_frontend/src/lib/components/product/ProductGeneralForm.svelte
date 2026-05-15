<script lang="ts">
    import type { Product, Tax } from '$lib/api/products';
    import type { Category } from '$lib/api/categories';
    import Button from '../ui/Button.svelte';

    let { formData = $bindable(), categories, taxes = [], isUploading = $bindable(), handleImageUpload, removeImage } = $props<{
        formData: Partial<Product>;
        categories: Category[];
        taxes?: Tax[];
        isUploading: boolean;
        handleImageUpload: (e: Event) => void;
        removeImage: () => void;
    }>();
</script>

<div class="grid grid-cols-1 md:grid-cols-2 gap-8 animate-in fade-in slide-in-from-bottom-2">
    <div class="flex flex-col gap-6">
        <div class="form-control">
            <label class="label font-bold text-xs uppercase tracking-widest opacity-60">Nombre</label>
            <input type="text" placeholder="Ej: Café Americano" class="input input-bordered w-full focus:input-primary" bind:value={formData.name} />
        </div>
        <div class="grid grid-cols-2 gap-4">
            <div class="form-control">
                <label class="label font-bold text-xs uppercase tracking-widest opacity-60">Categoría</label>
                <select class="select select-bordered w-full focus:select-primary" bind:value={formData.category_id}>
                    <option disabled selected value={undefined}>Selecciona una categoría</option>
                    {#each categories as category}
                        <option value={category.id}>{category.name}</option>
                    {/each}
                </select>
            </div>
            <div class="form-control">
                <label class="label font-bold text-xs uppercase tracking-widest opacity-60">Impuesto</label>
                <select class="select select-bordered w-full focus:select-primary" bind:value={formData.tax_id}>
                    <option selected value={null}>Tasa Global / Por Defecto</option>
                    {#each taxes as tax}
                        <option value={tax.id}>{tax.name} ({tax.rate}%)</option>
                    {/each}
                </select>
            </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
            <div class="form-control">
                <label class="label font-bold text-xs uppercase tracking-widest opacity-60">Precio (Sin Tallas) ($)</label>
                <input type="number" step="0.01" class="input input-bordered w-full focus:input-primary" bind:value={formData.price} />
                <span class="text-[9px] opacity-40 mt-1 uppercase">Se ignora si añades tallas específicas.</span>
            </div>
            <div class="form-control">
                <label class="label font-bold text-xs uppercase tracking-widest opacity-60">Stock Inicial</label>
                <input type="number" class="input input-bordered w-full focus:input-primary" bind:value={formData.stock} />
            </div>
        </div>
    </div>
    <div class="flex flex-col gap-6">
        <div class="form-control">
            <label class="label font-bold text-xs uppercase tracking-widest opacity-60">Foto del Producto</label>
            <div class="flex flex-col gap-3">
                {#if formData.image_url}
                    <div class="relative group w-full aspect-video rounded-2xl overflow-hidden border border-base-300 bg-base-200">
                        <img src={formData.image_url} alt={formData.name} class="w-full h-full object-cover" />
                        <div class="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                            <Button variant="ghost" danger circle size="sm" onclick={removeImage} title="Eliminar Imagen">
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                            </Button>
                            <label class="w-10 h-10 bg-primary text-white rounded-full flex items-center justify-center cursor-pointer shadow-lg hover:shadow-primary/40 hover:-translate-y-0.5 transition-all duration-200" title="Cambiar Imagen">
                                <input type="file" class="hidden" accept="image/*" onchange={handleImageUpload} />
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a2 2 0 002 2h12a2 2 0 002-2v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
                            </label>
                        </div>
                    </div>
                {:else}
                    <label class="flex flex-col items-center justify-center w-full h-40 border-2 border-dashed border-base-300 rounded-2xl cursor-pointer hover:bg-base-200 transition-all gap-2 group">
                        <input type="file" class="hidden" accept="image/*" onchange={handleImageUpload} />
                        {#if isUploading}
                            <span class="loading loading-spinner text-primary"></span>
                        {:else}
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10 opacity-20 group-hover:opacity-40 transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                            <span class="text-[10px] font-black uppercase tracking-widest opacity-40">Subir Imagen</span>
                        {/if}
                    </label>
                {/if}
                <input type="text" placeholder="O pega una URL externa..." class="input input-bordered input-xs w-full focus:input-primary text-[10px]" bind:value={formData.image_url} />
            </div>
        </div>
        <div class="form-control">
            <label class="label font-bold text-xs uppercase tracking-widest opacity-60">Descripción</label>
            <textarea class="textarea textarea-bordered h-28 focus:textarea-primary" placeholder="Descripción del producto..." bind:value={formData.description}></textarea>
        </div>
        <div class="flex flex-wrap gap-6 items-center">
            <label class="label cursor-pointer justify-start gap-4">
                <span class="label-text font-bold">¿Producto Activo?</span>
                <input type="checkbox" class="toggle toggle-primary" bind:checked={formData.is_active} />
            </label>
            <label class="label cursor-pointer justify-start gap-4">
                <span class="label-text font-bold">¿Requiere Preparación en Cocina?</span>
                <input type="checkbox" class="toggle toggle-secondary" bind:checked={formData.requires_preparation} />
            </label>
        </div>
    </div>
</div>
