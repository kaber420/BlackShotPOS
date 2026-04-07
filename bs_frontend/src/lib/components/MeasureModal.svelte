<script lang="ts">
    import { ProductService, type Measure } from '$lib/api/products';
    import { onMount } from 'svelte';

    let { isOpen, onClose, onRefresh } = $props<{
        isOpen: boolean;
        onClose: () => void;
        onRefresh: () => void;
    }>();

    let measures = $state<Measure[]>([]);
    let isLoading = $state(false);
    let isSaving = $state(false);

    let newMeasure = $state<Partial<Measure>>({
        name: '',
        value: 0,
        unit: 'ml'
    });

    async function loadMeasures() {
        isLoading = true;
        try {
            measures = await ProductService.getMeasures();
        } catch (e) {
            console.error(e);
        } finally {
            isLoading = false;
        }
    }

    async function handleAdd() {
        if (!newMeasure.name || newMeasure.value === undefined) return;
        isSaving = true;
        try {
            await ProductService.createMeasure(newMeasure);
            newMeasure = { name: '', value: 0, unit: 'ml' };
            await loadMeasures();
            onRefresh();
        } catch (e) {
            console.error(e);
        } finally {
            isSaving = false;
        }
    }

    $effect(() => {
        if (isOpen) loadMeasures();
    });
</script>

{#if isOpen}
    <div class="modal modal-open">
        <div class="modal-box max-w-lg bg-base-100 border border-base-300">
            <h3 class="font-bold text-xl mb-4">Gestionar Medidas (Tallas)</h3>
            
            <div class="flex flex-col gap-4 mb-6">
                <div class="grid grid-cols-3 gap-2">
                    <div class="form-control">
                        <label class="label text-xs uppercase opacity-60 font-bold">Nombre</label>
                        <input type="text" placeholder="Chico" class="input input-bordered input-sm" bind:value={newMeasure.name} />
                    </div>
                    <div class="form-control">
                        <label class="label text-xs uppercase opacity-60 font-bold">Cantidad/Capacidad</label>
                        <input type="number" placeholder="Ej: 12" class="input input-bordered input-sm" bind:value={newMeasure.value} />
                    </div>
                    <div class="form-control">
                        <label class="label text-xs uppercase opacity-60 font-bold">Unidad</label>
                        <select class="select select-bordered select-sm" bind:value={newMeasure.unit}>
                            <option value="ml">ml</option>
                            <option value="oz">oz</option>
                            <option value="g">g</option>
                            <option value="pz">pz</option>
                        </select>
                    </div>
                </div>
                <button class="btn btn-primary btn-sm" onclick={handleAdd} disabled={isSaving || !newMeasure.name}>
                    {isSaving ? 'Añadiendo...' : 'Añadir Medida'}
                </button>
            </div>

            <div class="divider text-xs opacity-50 uppercase tracking-widest font-bold">Listado Actual</div>

            <div class="max-h-48 overflow-y-auto bg-base-200/50 rounded-lg p-2">
                {#if isLoading}
                    <div class="flex justify-center p-4"><span class="loading loading-spinner"></span></div>
                {:else if measures.length === 0}
                    <p class="text-center py-4 opacity-40 italic">No hay medidas creadas.</p>
                {:else}
                    <table class="table table-xs">
                        <thead>
                            <tr>
                                <th>Nombre</th>
                                <th>Especificación</th>
                            </tr>
                        </thead>
                        <tbody>
                            {#each measures as m}
                                <tr>
                                    <td class="font-bold">{m.name}</td>
                                    <td>{m.value} {m.unit}</td>
                                </tr>
                            {/each}
                        </tbody>
                    </table>
                {/if}
            </div>

            <div class="modal-action">
                <button class="btn" onclick={onClose}>Cerrar</button>
            </div>
        </div>
        <button class="modal-backdrop" onclick={onClose}></button>
    </div>
{/if}
