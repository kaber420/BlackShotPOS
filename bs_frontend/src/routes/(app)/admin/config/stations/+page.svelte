<script lang="ts">
    /**
     * Blackshot POS - Production Stations / Areas Management
     * -----------------------------------------------------
     * UI for creating and managing kitchen, bar, and other production stations.
     */
    import { onMount } from 'svelte';
    import { ProductionAreaService, type ProductionArea } from '$lib/api/production_areas';
    import { addToast } from '$lib/toast.svelte.js';
    import Button from '$lib/components/ui/Button.svelte';

    let areas = $state<ProductionArea[]>([]);
    let isLoading = $state(true);
    let isSaving = $state(false);

    // Form state for new/edit
    let editingArea = $state<Partial<ProductionArea> | null>(null);
    let newArea = $state<Partial<ProductionArea>>({
        name: '',
        description: '',
        is_active: true
    });

    async function loadAreas() {
        isLoading = true;
        try {
            areas = await ProductionAreaService.getAll();
        } catch (e) {
            addToast("Error al cargar estaciones", "error");
            console.error(e);
        } finally {
            isLoading = false;
        }
    }

    async function handleSave() {
        if (!newArea.name) return;
        isSaving = true;
        try {
            if (editingArea?.id) {
                await ProductionAreaService.update(editingArea.id, newArea);
                addToast("Estación actualizada", "success");
            } else {
                await ProductionAreaService.create(newArea);
                addToast("Estación creada", "success");
            }
            newArea = { name: '', description: '', is_active: true };
            editingArea = null;
            await loadAreas();
        } catch (e) {
            addToast("Error al guardar", "error");
        } finally {
            isSaving = false;
        }
    }

    function startEdit(area: ProductionArea) {
        editingArea = { ...area };
        newArea = { ...area };
    }

    function cancelEdit() {
        editingArea = null;
        newArea = { name: '', description: '', is_active: true };
    }

    async function handleDelete(id: number) {
        if (!confirm("¿Eliminar esta estación? Las categorías vinculadas quedarán sin destino de impresión.")) return;
        try {
            await ProductionAreaService.delete(id);
            addToast("Estación eliminada", "success");
            await loadAreas();
        } catch (e) {
            addToast("Error al eliminar", "error");
        }
    }

    onMount(loadAreas);
</script>

<div class="p-6 lg:p-10 max-w-5xl mx-auto flex-1 min-h-0 overflow-y-auto w-full space-y-8 animate-in fade-in slide-in-from-bottom-4">
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div class="flex flex-col gap-1">
            <h1 class="text-4xl font-black tracking-tight flex items-center gap-3 uppercase">
                <div class="w-12 h-12 bg-secondary rounded-2xl flex items-center justify-center text-secondary-content shadow-lg shadow-secondary/20">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-7 h-7">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5m-9-6h.008v.008H12v-.008zM12 15h.008v.008H12V15zm0 2.25h.008v.008H12v-.008zM9.75 15h.008v.008H9.75V15zm0 2.25h.008v.008H9.75v-.008zM7.5 15h.008v.008H7.5V15zm0 2.25h.008v.008H7.5v-.008zm6.75-4.5h.008v.008h-.008v-.008zm0 2.25h.008v.008h-.008V15zm0 2.25h.008v.008h-.008v-.008zm2.25-4.5h.008v.008H16.5v-.008zm0 2.25h.008v.008H16.5V15z" />
                    </svg>
                </div>
                Estaciones de Producción
            </h1>
            <p class="text-base-content/60 font-medium ml-1">Configura dónde se preparan tus productos (Cocina, Bar, etc.)</p>
        </div>
        
        <a href="/admin/config" class="btn btn-ghost gap-2 font-bold uppercase text-xs">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-4 h-4">
                <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg>
            Volver a Configuración
        </a>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <!-- List Panel -->
        <div class="lg:col-span-2 space-y-4">
            <div class="bg-base-100 rounded-3xl border border-base-200 shadow-xl overflow-hidden">
                <table class="table table-lg">
                    <thead class="bg-base-200/50">
                        <tr>
                            <th class="font-black text-xs uppercase tracking-widest">Estación</th>
                            <th class="font-black text-xs uppercase tracking-widest">Descripción</th>
                            <th class="font-black text-xs uppercase tracking-widest">Estado</th>
                            <th class="font-black text-xs uppercase tracking-widest text-right">Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#if isLoading}
                            {#each Array(3) as _}
                                <tr class="animate-pulse">
                                    <td colspan="4"><div class="h-12 bg-base-200 rounded-xl w-full"></div></td>
                                </tr>
                            {/each}
                        {:else if areas.length === 0}
                            <tr>
                                <td colspan="4" class="text-center py-12 opacity-50 italic font-medium">No hay estaciones configuradas.</td>
                            </tr>
                        {:else}
                            {#each areas as area}
                                <tr class="hover:bg-base-200/30 transition-colors group">
                                    <td>
                                        <div class="font-black text-lg">{area.name}</div>
                                    </td>
                                    <td class="text-sm opacity-60 font-medium">{area.description || '—'}</td>
                                    <td>
                                        <span class="badge {area.is_active ? 'badge-success' : 'badge-ghost'} badge-sm font-black p-2.5">
                                            {area.is_active ? 'ACTIVA' : 'INACTIVA'}
                                        </span>
                                    </td>
                                    <td class="text-right">
                                        <div class="flex justify-end gap-2">
                                            <Button variant="ghost" size="sm" class="text-primary" onclick={() => startEdit(area)}>Editar</Button>
                                            <Button variant="ghost" size="sm" danger onclick={() => handleDelete(area.id)}>Eliminar</Button>
                                        </div>
                                    </td>
                                </tr>
                            {/each}
                        {/if}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Form Panel -->
        <div class="lg:col-span-1">
            <div class="card bg-base-100 border border-base-200 shadow-xl sticky top-6">
                <div class="card-body gap-6">
                    <h3 class="text-xl font-black uppercase tracking-tight flex items-center gap-2">
                        <span class="w-1.5 h-6 bg-primary rounded-full"></span>
                        {editingArea ? 'Editar Estación' : 'Nueva Estación'}
                    </h3>

                    <div class="form-control w-full">
                        <label class="label"><span class="label-text font-bold uppercase text-[10px] opacity-60">Nombre de la Estación</span></label>
                        <input type="text" bind:value={newArea.name} placeholder="Ej: Cocina, Bar, Horno" class="input input-bordered font-bold focus:border-primary" />
                    </div>

                    <div class="form-control w-full">
                        <label class="label"><span class="label-text font-bold uppercase text-[10px] opacity-60">Descripción</span></label>
                        <textarea bind:value={newArea.description} placeholder="Propósito de esta estación..." class="textarea textarea-bordered font-bold h-24 focus:border-primary"></textarea>
                    </div>

                    <div class="form-control">
                        <label class="label cursor-pointer justify-start gap-4">
                            <input type="checkbox" bind:checked={newArea.is_active} class="toggle toggle-primary" />
                            <span class="label-text font-bold">Estación Activa</span>
                        </label>
                    </div>

                    <div class="flex flex-col gap-2 pt-4">
                        <Button variant="primary" size="lg" class="w-full font-black uppercase" onclick={handleSave} isLoading={isSaving}>
                            {editingArea ? 'Guardar Cambios' : 'Crear Estación'}
                        </Button>
                        {#if editingArea}
                            <Button variant="ghost" size="lg" class="w-full font-bold opacity-60" onclick={cancelEdit}>
                                Cancelar
                            </Button>
                        {/if}
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
