<script lang="ts">
    import { onMount } from 'svelte';
    import { fetchApi } from '$lib/api';
    import Toolbar from '$lib/components/ui/Toolbar.svelte';

    let audits: any[] = $state([]);
    let error: string | null = $state(null);
    let loading = $state(true);
    
    // Filtro por categoría
    let selectedCategory: string = $state('ALL');

    onMount(async () => {
        try {
            audits = await fetchApi('/api/v1/pos/system/audit/audits');
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

    // Derivar audits filtrados usando Runes
    let filteredAudits = $derived(
        selectedCategory === 'ALL' 
            ? audits 
            : audits.filter(a => a.category === selectedCategory)
    );
</script>

<div class="p-4 lg:p-8 space-y-8 flex-1 min-h-0 overflow-y-auto w-full">
    
    <!-- Unified Header Toolbar -->
    <Toolbar title="Bitácora de Auditoría">
        {#snippet left()}
            <a href="/admin" class="btn btn-ghost btn-sm font-black gap-1 rounded-xl uppercase tracking-wider text-xs">
                ← Volver al Panel
            </a>
        {/snippet}
        
        {#snippet right()}
            <div class="tabs tabs-boxed bg-base-200 p-1 rounded-xl shadow-inner flex items-center">
                <button 
                    class="tab tab-sm rounded-lg font-bold transition-all duration-200 {selectedCategory === 'ALL' ? 'tab-active bg-primary text-primary-content shadow-md' : 'opacity-60'}" 
                    onclick={() => selectedCategory = 'ALL'}>Todo</button>
                <button 
                    class="tab tab-sm rounded-lg font-bold transition-all duration-200 {selectedCategory === 'security' ? 'tab-active bg-primary text-primary-content shadow-md' : 'opacity-60'}" 
                    onclick={() => selectedCategory = 'security'}>Seguridad</button>
                <button 
                    class="tab tab-sm rounded-lg font-bold transition-all duration-200 {selectedCategory === 'sales' ? 'tab-active bg-primary text-primary-content shadow-md' : 'opacity-60'}" 
                    onclick={() => selectedCategory = 'sales'}>Ventas</button>
                <button 
                    class="tab tab-sm rounded-lg font-bold transition-all duration-200 {selectedCategory === 'inventory' ? 'tab-active bg-primary text-primary-content shadow-md' : 'opacity-60'}" 
                    onclick={() => selectedCategory = 'inventory'}>Inventario</button>
                <button 
                    class="tab tab-sm rounded-lg font-bold transition-all duration-200 {selectedCategory === 'config' ? 'tab-active bg-primary text-primary-content shadow-md' : 'opacity-60'}" 
                    onclick={() => selectedCategory = 'config'}>Sistema</button>
            </div>
        {/snippet}
    </Toolbar>

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
                            <th class="font-bold tracking-widest text-xs uppercase opacity-75">Usuario</th>
                            <th class="font-bold tracking-widest text-xs uppercase opacity-75">Categoría / Acción</th>
                            <th class="font-bold tracking-widest text-xs uppercase opacity-75">Objetivo</th>
                            <th class="font-bold tracking-widest text-xs uppercase opacity-75">Motivo / Detalles</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each filteredAudits as log}
                            <tr>
                                <td class="font-medium opacity-80 whitespace-nowrap">{formatDate(log.timestamp)}</td>
                                <td class="font-bold">{log.actor_name}</td>
                                <td>
                                    <div class="flex flex-col gap-1 items-start">
                                        <span class="text-[10px] font-bold uppercase opacity-50 tracking-widest">{log.category}</span>
                                        <span class="badge badge-sm font-bold uppercase {log.action.includes('DENIED') || log.action.includes('CANCELLED') ? 'badge-error' : 'badge-neutral'}">
                                            {log.action}
                                        </span>
                                    </div>
                                </td>
                                <td class="font-mono text-xs opacity-75 select-all">
                                    {#if log.target_type && log.target_id}
                                        {log.target_type}: {log.target_id}
                                    {:else}
                                        <span class="opacity-30">N/A</span>
                                    {/if}
                                </td>
                                <td class="whitespace-normal min-w-[200px] text-sm">
                                    {#if log.reason}
                                        <div class="italic mb-1">"{log.reason}"</div>
                                    {/if}
                                    {#if log.changes_json}
                                        <div class="text-xs opacity-60 font-mono mt-1 break-all">
                                            JSON: {log.changes_json}
                                        </div>
                                    {/if}
                                </td>
                            </tr>
                        {:else}
                            <tr>
                                <td colspan="5" class="text-center py-12 opacity-50 font-bold">
                                    No hay registros recientes para esta vista.
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        </div>
    {/if}
</div>
