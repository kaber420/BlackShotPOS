<script lang="ts">
    import { CategoryService } from '$lib/api/categories';
    import type { Category } from '$lib/api/categories';
    import { onMount } from 'svelte';
    import Button from './ui/Button.svelte';

    let { isOpen, onClose, onRefresh } = $props<{
        isOpen: boolean;
        onClose: () => void;
        onRefresh: () => void;
    }>();

    let categories = $state<Category[]>([]);
    let isLoading = $state(false);
    let isSaving = $state(false);
    let newCategory = $state<Partial<Category>>({
        name: '',
        description: '',
        is_modifier_category: false
    });
    let errorMessage = $state('');

    async function loadCategories() {
        isLoading = true;
        try {
            categories = await CategoryService.getAll();
        } catch (err) {
            console.error('Error loading categories:', err);
        } finally {
            isLoading = false;
        }
    }

    $effect(() => {
        if (isOpen) {
            loadCategories();
        }
    });

    async function handleAdd() {
        if (!newCategory.name) return;
        isSaving = true;
        errorMessage = '';
        try {
            await CategoryService.create(newCategory);
            newCategory = { name: '', description: '', is_modifier_category: false };
            await loadCategories();
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
            await loadCategories();
            onRefresh();
        } catch (err) {
            alert('No se pudo eliminar la categoría. Puede que esté en uso.');
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
                        <input 
                            type="text" 
                            placeholder="Nombre de categoría (ej: Bebidas)" 
                            class="input input-bordered w-full input-sm focus:input-primary" 
                            bind:value={newCategory.name} 
                        />
                        <div class="flex gap-2">
                            <input 
                                class="input input-bordered flex-1 input-sm focus:input-primary" 
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
                    <h4 class="text-xs font-bold uppercase tracking-widest opacity-50 mb-3">Categorías Existentes</h4>
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
                                    <div class="flex flex-col">
                                            <span class="font-bold">{cat.name}</span>
                                            {#if cat.description}
                                                <span class="text-xs opacity-50">{cat.description}</span>
                                            {/if}
                                        </div>
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
