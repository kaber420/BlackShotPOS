<script lang="ts">
    import { CategoryService } from '$lib/api/categories';
    import type { Category } from '$lib/api/categories';
    import { onMount } from 'svelte';
    import Button from './ui/Button.svelte';
    import { ProductionAreaService, type ProductionArea } from '$lib/api/production_areas';

    let { isOpen, onClose, onRefresh } = $props<{
        isOpen: boolean;
        onClose: () => void;
        onRefresh: () => void;
    }>();

    let categories = $state<Category[]>([]);
    let productionAreas = $state<ProductionArea[]>([]);
    let isLoading = $state(false);
    let isSaving = $state(false);
    let newCategory = $state<Partial<Category>>({
        name: '',
        description: '',
        is_modifier_category: false,
        production_area_id: undefined
    });
    let errorMessage = $state('');

    async function loadData() {
        isLoading = true;
        try {
            const [cats, areas] = await Promise.all([
                CategoryService.getAll(),
                ProductionAreaService.getAll()
            ]);
            categories = cats;
            productionAreas = areas;
        } catch (err) {
            console.error('Error loading data:', err);
        } finally {
            isLoading = false;
        }
    }

    $effect(() => {
        if (isOpen) {
            loadData();
        }
    });

    async function handleAdd() {
        if (!newCategory.name) return;
        isSaving = true;
        errorMessage = '';
        try {
            await CategoryService.create(newCategory);
            newCategory = { name: '', description: '', is_modifier_category: false, production_area_id: undefined };
            await loadData();
            onRefresh(); // Refresh parent to get new names
        } catch (err) {
            errorMessage = 'Error al crear la categoría.';
        } finally {
            isSaving = false;
        }
    }

    async function handleDelete(id: number) {
        if (!confirm('¿Seguro que deseas eliminar esta categoría? (Afectará a los productos asignados)')) return;
        try {
            await CategoryService.delete(id);
            await loadData();
            onRefresh();
        } catch (err) {
            alert('No se pudo eliminar la categoría. Puede que esté en uso.');
        }
    }

    function getAreaName(id?: number) {
        if (!id) return 'Sin destino';
        return productionAreas.find(a => a.id === id)?.name || 'Destino desconocido';
    }

    async function updateCategoryArea(cat: Category, areaId: string) {
        try {
            const id = areaId ? parseInt(areaId) : undefined;
            await CategoryService.update(cat.id!, { ...cat, production_area_id: id });
            await loadData();
            onRefresh();
        } catch (err) {
            console.error('Error updating category area:', err);
        }
    }
</script>

{#if isOpen}
    <div class="modal modal-open">
        <div class="modal-box max-w-xl bg-base-100 border border-base-300 shadow-2xl p-0 overflow-hidden">
            <header class="bg-base-200/50 p-6 border-b border-base-300">
                <h3 class="font-bold text-xl flex items-center gap-2">
                    <span class="p-2 bg-secondary/10 rounded-lg text-secondary">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>
                    </span>
                    Gestión de Categorías
                </h3>
            </header>

            <div class="p-6 flex flex-col gap-6">
                <!-- Formulario de Nueva Categoría -->
                <div class="bg-base-200/30 p-4 rounded-xl border border-base-300/50">
                    <h4 class="text-xs font-bold uppercase tracking-widest opacity-50 mb-3">Nueva Categoría</h4>
                    <div class="flex flex-col gap-3">
                        <div class="flex gap-2">
                            <input 
                                type="text" 
                                placeholder="Nombre (ej: Bebidas)" 
                                class="input input-bordered flex-1 input-sm font-bold focus:input-primary" 
                                bind:value={newCategory.name} 
                            />
                            <select 
                                class="select select-bordered select-sm font-bold focus:select-primary"
                                bind:value={newCategory.production_area_id}
                            >
                                <option value={undefined}>Sin destino</option>
                                {#each productionAreas as area}
                                    <option value={area.id}>{area.name}</option>
                                {/each}
                            </select>
                        </div>
                        <div class="flex gap-2">
                            <input 
                                class="input input-bordered flex-1 input-sm focus:input-primary" 
                                placeholder="Descripción corta..."
                                bind:value={newCategory.description} 
                            />
                            <Button 
                                size="sm" 
                                onclick={handleAdd} 
                                isLoading={isSaving}
                                disabled={!newCategory.name}
                                class="px-6"
                            >
                                Añadir
                            </Button>
                        </div>
                    </div>
                </div>

                <!-- Lista de Categorías -->
                <div>
                    <div class="flex items-center justify-between mb-3">
                        <h4 class="text-xs font-bold uppercase tracking-widest opacity-50">Categorías Existentes</h4>
                        <a href="/admin/config/stations" class="text-[10px] font-black uppercase text-primary hover:underline flex items-center gap-1">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-3 h-3">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                            </svg>
                            Gestionar Estaciones
                        </a>
                    </div>
                    {#if isLoading}
                        <div class="flex justify-center py-8">
                            <span class="loading loading-dots loading-md text-primary"></span>
                        </div>
                    {:else if categories.length === 0}
                        <div class="text-center py-8 opacity-40 italic text-sm">No hay categorías registradas.</div>
                    {:else}
                        <div class="flex flex-col gap-2 max-h-[300px] overflow-y-auto pr-2">
                            {#each categories as cat}
                                <div class="flex items-center justify-between p-3 bg-base-100 rounded-lg border border-base-200 hover:border-primary/30 transition-all group">
                                    <div class="flex flex-col flex-1">
                                        <span class="font-bold">{cat.name}</span>
                                        {#if cat.description}
                                            <span class="text-xs opacity-50">{cat.description}</span>
                                        {/if}
                                    </div>
                                    
                                    <div class="flex items-center gap-3">
                                        <select 
                                            class="select select-ghost select-xs font-bold opacity-60 hover:opacity-100 focus:opacity-100"
                                            value={cat.production_area_id}
                                            onchange={(e) => updateCategoryArea(cat, e.currentTarget.value)}
                                        >
                                            <option value="">Sin destino</option>
                                            {#each productionAreas as area}
                                                <option value={area.id}>{area.name}</option>
                                            {/each}
                                        </select>

                                        <Button 
                                            variant="ghost" 
                                            size="sm" 
                                            danger 
                                            circle 
                                            class="opacity-0 group-hover:opacity-100 transition-opacity"
                                            onclick={() => handleDelete(cat.id!)}
                                            aria-label="Eliminar categoría"
                                            title="Eliminar categoría"
                                        >
                                            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                                        </Button>
                                    </div>
                                </div>
                            {/each}
                        </div>
                    {/if}
                </div>
            </div>

            <div class="p-6 bg-base-200/50 flex justify-end border-t border-base-300">
                <Button variant="ghost" onclick={onClose}>Cerrar Panel</Button>
            </div>
        </div>
        <button 
            class="modal-backdrop bg-black/50 border-none w-full h-full fixed inset-0 cursor-default" 
            onclick={onClose}
            aria-label="Cerrar modal"
        ></button>
    </div>
{/if}
