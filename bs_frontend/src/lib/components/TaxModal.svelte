<script lang="ts">
    import { onMount } from 'svelte';
    import Button from './ui/Button.svelte';
    import { ProductService, type Tax } from '$lib/api/products';
    import { addToast } from '$lib/toast.svelte';
    let { isOpen = false, onClose }: { isOpen?: boolean, onClose: () => void } = $props();
    let taxes = $state<Tax[]>([]);
    let isLoading = $state(false);
    let editingTax = $state<Partial<Tax> | null>(null);
    let isSaving = $state(false);

    $effect(() => {
        if (isOpen) {
            loadTaxes();
        }
    });

    async function loadTaxes() {
        isLoading = true;
        try {
            taxes = await ProductService.getTaxes();
        } catch (e) {
            addToast("Error al cargar impuestos: " + e, "error");
        } finally {
            isLoading = false;
        }
    }

    function handleEdit(tax: Tax) {
        editingTax = { ...tax };
    }

    function handleCreate() {
        editingTax = {
            name: '',
            rate: 0
        };
    }

    function cancelEdit() {
        editingTax = null;
    }

    async function saveTax() {
        if (!editingTax || !editingTax.name || editingTax.rate === undefined) {
            addToast("El nombre y la tasa son obligatorios", "error");
            return;
        }

        isSaving = true;
        try {
            if (editingTax.id) {
                await ProductService.updateTax(editingTax.id, editingTax);
                addToast("Impuesto actualizado", "success");
            } else {
                await ProductService.createTax(editingTax);
                addToast("Impuesto creado", "success");
            }
            editingTax = null;
            await loadTaxes();
        } catch (e) {
            addToast("Error al guardar impuesto: " + e, "error");
        } finally {
            isSaving = false;
        }
    }

    async function deleteTax(id: number) {
        if (!confirm("¿Estás seguro de eliminar este impuesto? Los productos asociados podrían verse afectados.")) return;
        
        try {
            await ProductService.deleteTax(id);
            addToast("Impuesto eliminado", "success");
            await loadTaxes();
        } catch (e) {
            addToast("Error al eliminar impuesto: " + e, "error");
        }
    }
</script>
{#if isOpen}
    <div class="modal modal-open">
        <div class="modal-box max-w-3xl bg-base-100 border border-base-300 shadow-2xl p-0 overflow-hidden rounded-[2rem]">
            <header class="bg-base-200/50 p-6 border-b border-base-300 flex justify-between items-center">
                <h3 class="font-black text-xl flex items-center gap-3 uppercase tracking-tight">Gestión de Impuestos</h3>
                <button class="btn btn-ghost btn-sm btn-circle" onclick={onClose}>✕</button>
            </header>
            <div class="p-6 flex flex-col gap-6 w-full max-h-[70vh] overflow-y-auto">
                <p class="text-sm opacity-70">
                    Define los diferentes tipos de impuestos aplicables a los productos (ej. IVA 16%, IEPS 8%, Tasa 0%).
                </p>

                {#if editingTax}
                    <!-- Formulario de Edición/Creación -->
                    <div class="bg-base-200 p-6 rounded-2xl border border-base-300 space-y-4 animate-in fade-in slide-in-from-top-4">
                        <h3 class="text-lg font-black uppercase">
                            {editingTax.id ? 'Editar Impuesto' : 'Nuevo Impuesto'}
                        </h3>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div class="form-control">
                                <label class="label"><span class="label-text font-black text-[10px] uppercase opacity-50">Nombre del Impuesto</span></label>
                                <input type="text" bind:value={editingTax.name} class="input input-bordered font-bold focus:border-primary rounded-xl" placeholder="Ej: IVA 16%" />
                            </div>
                            <div class="form-control">
                                <label class="label"><span class="label-text font-black text-[10px] uppercase opacity-50">Tasa (Porcentaje)</span></label>
                                <div class="flex items-center gap-2">
                                    <input type="number" step="0.01" bind:value={editingTax.rate} class="input input-bordered font-bold text-center focus:border-primary rounded-xl w-full" />
                                    <span class="font-bold opacity-50">%</span>
                                </div>
                            </div>
                        </div>
                        <div class="flex justify-end gap-2 mt-4 pt-4 border-t border-base-300">
                            <Button variant="ghost" onclick={cancelEdit} disabled={isSaving}>Cancelar</Button>
                            <Button variant="primary" onclick={saveTax} isLoading={isSaving}>Guardar</Button>
                        </div>
                    </div>
                {:else}
                    <!-- Lista de Impuestos -->
                    <div class="flex justify-between items-center mb-2">
                        <h3 class="text-lg font-black uppercase opacity-70">Impuestos Disponibles</h3>
                        <Button variant="primary" size="sm" onclick={handleCreate} class="gap-2">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-4 h-4"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
                            Añadir Impuesto
                        </Button>
                    </div>

                    {#if isLoading}
                        <div class="flex justify-center p-8">
                            <span class="loading loading-spinner loading-lg text-primary"></span>
                        </div>
                    {:else if taxes.length === 0}
                        <div class="text-center py-10 opacity-50">
                            No hay impuestos configurados. Usa el botón superior para añadir uno.
                        </div>
                    {:else}
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {#each taxes as tax}
                                <div class="card bg-base-100 border border-base-200 shadow-sm">
                                    <div class="card-body p-4 flex flex-row items-center justify-between gap-4">
                                        <div>
                                            <h4 class="font-black text-lg">{tax.name}</h4>
                                            <p class="text-sm opacity-70 font-bold">{tax.rate}%</p>
                                        </div>
                                        <div class="flex gap-2">
                                            <button class="btn btn-ghost btn-sm btn-circle text-blue-500 hover:bg-blue-500/10" onclick={() => handleEdit(tax)}>
                                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5"><path stroke-linecap="round" stroke-linejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487zm0 0L19.5 7.125" /></svg>
                                            </button>
                                            <button class="btn btn-ghost btn-sm btn-circle text-red-500 hover:bg-red-500/10" onclick={() => deleteTax(tax.id!)}>
                                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5"><path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" /></svg>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            {/each}
                        </div>
                    {/if}
                {/if}
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
