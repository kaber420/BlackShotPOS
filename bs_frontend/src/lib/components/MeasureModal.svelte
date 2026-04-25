<script lang="ts">
    import { ProductService, type Measure } from '$lib/api/products';
    import { onMount } from 'svelte';
    import Button from './ui/Button.svelte';

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
        <div class="modal-box max-w-lg bg-base-100 border border-base-300 shadow-2xl p-0 overflow-hidden">
            <header class="p-6 bg-base-200/50 border-b border-base-300">
                <h3 class="font-bold text-xl flex items-center gap-2">
                    <span class="p-2 bg-primary/10 rounded-lg text-primary">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 01-6.001 0M18 7l-3 9m3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" /></svg>
                    </span>
                    Gestionar Medidas (Tallas)
                </h3>
            </header>
            
            <div class="p-8 flex flex-col gap-4">
                <div class="grid grid-cols-3 gap-2">
                    <div class="form-control">
                        <label class="label text-xs uppercase opacity-60 font-bold" for="m_name">Nombre</label>
                        <input id="m_name" type="text" placeholder="Chico" class="input input-bordered input-sm" bind:value={newMeasure.name} />
                    </div>
                    <div class="form-control">
                        <label class="label text-xs uppercase opacity-60 font-bold" for="m_val">Cantidad/Capacidad</label>
                        <input id="m_val" type="number" placeholder="Ej: 12" class="input input-bordered input-sm" bind:value={newMeasure.value} />
                    </div>
                    <div class="form-control">
                        <label class="label text-xs uppercase opacity-60 font-bold" for="m_unit">Unidad</label>
                        <select id="m_unit" class="select select-bordered select-sm" bind:value={newMeasure.unit}>
                            <option value="ml">ml</option>
                            <option value="oz">oz</option>
                            <option value="g">g</option>
                            <option value="pz">pz</option>
                        </select>
                    </div>
                </div>
                <Button variant="primary" size="md" class="w-full mt-2" onclick={handleAdd} isLoading={isSaving} disabled={!newMeasure.name}>
                    Añadir Medida
                </Button>
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

            <div class="p-6 bg-base-200/50 flex justify-end gap-3 border-t border-base-300">
                <Button variant="ghost" onclick={onClose}>Cerrar</Button>
            </div>
        </div>
        <button class="modal-backdrop bg-black/60" onclick={onClose}></button>
    </div>
{/if}
