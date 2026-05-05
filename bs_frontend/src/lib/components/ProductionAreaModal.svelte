<script lang="ts">
    /**
     * ProductionAreaModal - Reusable modal for creating and managing Production Areas
     * Includes configuration for printers (IP, Port, Type).
     */
    import { ProductionAreaService, type ProductionArea } from '$lib/api/production_areas';
    import { addToast } from '$lib/toast.svelte.js';
    import Button from './ui/Button.svelte';
    import { onMount } from 'svelte';

    let { isOpen, onClose, onRefresh } = $props<{
        isOpen: boolean;
        onClose: () => void;
        onRefresh?: () => void;
    }>();

    let areas = $state<ProductionArea[]>([]);
    let isLoading = $state(false);
    let isSaving = $state(false);
    
    // Form state
    let editingId = $state<number | null>(null);
    let formData = $state<Partial<ProductionArea>>({
        name: '',
        description: '',
        printer_ip: '',
        printer_port: 9100,
        printer_type: 'network',
        is_active: true
    });

    async function loadData() {
        isLoading = true;
        try {
            areas = await ProductionAreaService.getAll();
        } catch (err) {
            console.error('Error loading production areas:', err);
            addToast("Error al cargar áreas", "error");
        } finally {
            isLoading = false;
        }
    }

    $effect(() => {
        if (isOpen) {
            loadData();
            resetForm();
        }
    });

    function resetForm() {
        editingId = null;
        formData = {
            name: '',
            description: '',
            printer_ip: '',
            printer_port: 9100,
            printer_type: 'network',
            is_active: true
        };
    }

    function startEdit(area: ProductionArea) {
        editingId = area.id;
        formData = { ...area };
    }

    async function handleSave() {
        if (!formData.name) {
            addToast("El nombre es obligatorio", "warning");
            return;
        }
        
        isSaving = true;
        try {
            if (editingId) {
                await ProductionAreaService.update(editingId, formData);
                addToast("Área actualizada correctamente", "success");
            } else {
                await ProductionAreaService.create(formData);
                addToast("Área creada correctamente", "success");
            }
            resetForm();
            await loadData();
            if (onRefresh) onRefresh();
        } catch (err) {
            console.error('Error saving production area:', err);
            addToast("Error al guardar el área", "error");
        } finally {
            isSaving = false;
        }
    }

    async function handleDelete(id: number) {
        if (!confirm('¿Seguro que deseas eliminar esta área de producción? Las categorías vinculadas podrían quedar sin destino.')) return;
        
        try {
            await ProductionAreaService.delete(id);
            addToast("Área eliminada", "success");
            await loadData();
            if (onRefresh) onRefresh();
        } catch (err) {
            console.error('Error deleting production area:', err);
            addToast("No se pudo eliminar el área", "error");
        }
    }
</script>

{#if isOpen}
    <div class="modal modal-open">
        <div class="modal-box max-w-4xl bg-base-100 border border-base-300 shadow-2xl p-0 overflow-hidden rounded-[2rem]">
            <header class="bg-base-200/50 p-6 border-b border-base-300 flex justify-between items-center">
                <h3 class="font-black text-xl flex items-center gap-3 uppercase tracking-tight">
                    <span class="p-2 bg-secondary/10 rounded-xl text-secondary">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                        </svg>
                    </span>
                    Gestión de Áreas de Producción
                </h3>
                <button class="btn btn-ghost btn-sm btn-circle" onclick={onClose}>✕</button>
            </header>

            <div class="grid grid-cols-1 md:grid-cols-2 h-[600px]">
                <!-- Form Side -->
                <div class="p-8 border-r border-base-200 flex flex-col gap-6 overflow-y-auto bg-base-100">
                    <div class="flex items-center gap-2">
                        <span class="w-1.5 h-6 bg-primary rounded-full"></span>
                        <h4 class="font-black uppercase tracking-widest text-xs opacity-60">
                            {editingId ? 'Editar Área' : 'Nueva Área de Producción'}
                        </h4>
                    </div>

                    <div class="form-control w-full">
                        <label class="label"><span class="label-text font-black text-[10px] uppercase opacity-50">Nombre de la Estación</span></label>
                        <input type="text" bind:value={formData.name} placeholder="Ej: Cocina, Bar, Horno" class="input input-bordered font-bold focus:border-primary rounded-xl" />
                    </div>

                    <div class="form-control w-full">
                        <label class="label"><span class="label-text font-black text-[10px] uppercase opacity-50">Descripción</span></label>
                        <textarea bind:value={formData.description} placeholder="¿Qué se prepara aquí?" class="textarea textarea-bordered font-bold h-20 focus:border-primary rounded-xl"></textarea>
                    </div>

                    <div class="divider text-[10px] font-black uppercase opacity-30 tracking-[0.2em]">Configuración de Impresión</div>

                    <div class="grid grid-cols-2 gap-4">
                        <div class="form-control w-full">
                            <label class="label"><span class="label-text font-black text-[10px] uppercase opacity-50">Tipo de Impresora</span></label>
                            <select bind:value={formData.printer_type} class="select select-bordered font-bold focus:border-primary rounded-xl">
                                <option value="network">Red (Ethernet/WiFi)</option>
                                <option value="bluetooth">Bluetooth</option>
                                <option value="usb">USB (Local)</option>
                            </select>
                        </div>
                        <div class="form-control w-full">
                            <label class="label"><span class="label-text font-black text-[10px] uppercase opacity-50">Puerto</span></label>
                            <input type="number" bind:value={formData.printer_port} class="input input-bordered font-bold text-center focus:border-primary rounded-xl" />
                        </div>
                    </div>

                    <div class="form-control w-full">
                        <label class="label"><span class="label-text font-black text-[10px] uppercase opacity-50">Dirección IP / Host</span></label>
                        <input type="text" bind:value={formData.printer_ip} placeholder="Ej: 192.168.1.50" class="input input-bordered font-mono text-sm focus:border-primary rounded-xl" />
                        {#if formData.printer_type === 'network'}
                            <label class="label"><span class="label-text-alt opacity-50 italic">Asegúrate que la impresora tenga IP estática.</span></label>
                        {/if}
                    </div>

                    <div class="form-control">
                        <label class="label cursor-pointer justify-start gap-4">
                            <input type="checkbox" bind:checked={formData.is_active} class="toggle toggle-primary" />
                            <span class="label-text font-bold">Área Operativa</span>
                        </label>
                    </div>

                    <div class="flex flex-col gap-2 pt-4 mt-auto">
                        <Button variant="primary" size="lg" class="w-full font-black uppercase tracking-widest text-xs" onclick={handleSave} isLoading={isSaving}>
                            {editingId ? 'Guardar Cambios' : 'Crear Área'}
                        </Button>
                        {#if editingId}
                            <Button variant="ghost" size="md" class="w-full font-bold opacity-50" onclick={resetForm}>
                                Cancelar Edición
                            </Button>
                        {/if}
                    </div>
                </div>

                <!-- List Side -->
                <div class="bg-base-200/30 flex flex-col overflow-hidden">
                    <div class="p-6 border-b border-base-200">
                        <h4 class="font-black uppercase tracking-widest text-xs opacity-60">Áreas Existentes</h4>
                    </div>

                    <div class="flex-1 overflow-y-auto p-4 space-y-3">
                        {#if isLoading}
                            {#each Array(4) as _}
                                <div class="h-20 bg-base-100 animate-pulse rounded-2xl"></div>
                            {/each}
                        {:else if areas.length === 0}
                            <div class="text-center py-20 opacity-40 italic text-sm">No hay áreas configuradas.</div>
                        {:else}
                            {#each areas as area}
                                <div class="bg-base-100 p-4 rounded-2xl border border-base-200 hover:border-primary/40 transition-all group flex items-center justify-between">
                                    <div class="flex-1">
                                        <div class="flex items-center gap-2">
                                            <span class="font-black text-base-content">{area.name}</span>
                                            {#if !area.is_active}
                                                <span class="badge badge-ghost badge-xs font-black text-[8px]">INACTIVA</span>
                                            {/if}
                                        </div>
                                        <p class="text-xs opacity-50 font-medium truncate max-w-[180px]">{area.description || 'Sin descripción'}</p>
                                        <div class="flex gap-2 mt-1">
                                            {#if area.printer_ip}
                                                <span class="text-[9px] font-black uppercase tracking-widest bg-base-200 px-1.5 py-0.5 rounded text-primary">
                                                    🖨️ {area.printer_ip}
                                                </span>
                                            {/if}
                                            <span class="text-[9px] font-black uppercase tracking-widest bg-base-200 px-1.5 py-0.5 rounded opacity-60">
                                                {area.printer_type}
                                            </span>
                                        </div>
                                    </div>
                                    <div class="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <Button variant="ghost" size="sm" circle class="text-primary" onclick={() => startEdit(area)}>
                                            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>
                                        </Button>
                                        <Button variant="ghost" size="sm" circle danger onclick={() => handleDelete(area.id)}>
                                            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                                        </Button>
                                    </div>
                                </div>
                            {/each}
                        {/if}
                    </div>
                </div>
            </div>

            <div class="p-6 bg-base-200/50 flex justify-end border-t border-base-300">
                <Button variant="ghost" class="font-bold" onclick={onClose}>Cerrar</Button>
            </div>
        </div>
        <button class="modal-backdrop bg-black/60 backdrop-blur-sm border-none w-full h-full fixed inset-0 cursor-default" onclick={onClose}></button>
    </div>
{/if}

<style>
    .modal-box {
        animation: modal-pop 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
    }

    @keyframes modal-pop {
        0% { transform: scale(0.9) translateY(20px); opacity: 0; }
        100% { transform: scale(1) translateY(0); opacity: 1; }
    }
</style>
