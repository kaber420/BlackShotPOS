<script lang="ts">
    import { onMount } from 'svelte';
    import { fetchApi } from '$lib/api';

    let audits: any[] = $state([]);
    let error: string | null = $state(null);
    let loading = $state(true);

    onMount(async () => {
        try {
            audits = await fetchApi('/api/v1/pos/audits');
        } catch (e: any) {
            error = e.message;
        } finally {
            loading = false;
        }
    });

    function formatDate(isoStr: string) {
        return new Date(isoStr).toLocaleString('es-MX', {
            dateStyle: 'short',
            timeStyle: 'short'
        });
    }
</script>

<div class="p-4 lg:p-8 max-w-7xl mx-auto space-y-8 flex-1 min-h-0 overflow-y-auto w-full w-full">
    <div class="flex items-center justify-between">
        <h1 class="text-4xl font-black text-primary flex items-center gap-3 tracking-tighter">
            🛡️ Auditoría Operativa
        </h1>
        <div class="text-sm font-bold opacity-50 uppercase tracking-widest">Bítacora de Eventos</div>
    </div>

    {#if loading}
        <div class="flex justify-center py-12">
            <span class="loading loading-spinner loading-lg text-primary"></span>
        </div>
    {:else if error}
        <div class="alert alert-error font-bold">
            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            <span>Error cargando bitácora: {error}</span>
        </div>
    {:else}
        <div class="card bg-base-100 shadow-xl border border-base-200 overflow-hidden">
            <div class="overflow-x-auto">
                <table class="table table-zebra w-full">
                    <thead class="bg-base-200/50">
                        <tr>
                            <th class="font-bold tracking-widest text-xs uppercase opacity-75">Sello de Tiempo</th>
                            <th class="font-bold tracking-widest text-xs uppercase opacity-75">Usuario Responsable</th>
                            <th class="font-bold tracking-widest text-xs uppercase opacity-75">Acción</th>
                            <th class="font-bold tracking-widest text-xs uppercase opacity-75">Asociado</th>
                            <th class="font-bold tracking-widest text-xs uppercase opacity-75">Motivo Referenciado</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each audits as log}
                            <tr>
                                <td class="font-medium opacity-80 whitespace-nowrap">{formatDate(log.timestamp)}</td>
                                <td class="font-bold">{log.actor_name}</td>
                                <td>
                                    <span class="badge badge-sm font-bold uppercase {log.action.includes('CANCELLED') ? 'badge-error' : 'badge-neutral'}">
                                        {log.action}
                                    </span>
                                </td>
                                <td class="font-mono text-xs opacity-75 select-all">
                                    {#if log.order_id}Ord: #{log.order_id}{/if}
                                    {#if log.order_item_id} | Itm: #{log.order_item_id}{/if}
                                </td>
                                <td class="whitespace-normal min-w-[200px] italic">"{log.reason}"</td>
                            </tr>
                        {:else}
                            <tr>
                                <td colspan="5" class="text-center py-12 opacity-50 font-bold">
                                    No hay registros recientes en la bitácora auditable.
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        </div>
    {/if}
</div>
