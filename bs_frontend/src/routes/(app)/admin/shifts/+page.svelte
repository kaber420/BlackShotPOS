<script lang="ts">
    import { onMount } from 'svelte';
    import { fetchApi } from '$lib/api';
    import { formatCurrency, formatDate, formatDateTime } from '$lib/utils';
    import { goto } from '$app/navigation';
    import Button from '$lib/components/ui/Button.svelte';
    import Toolbar from '$lib/components/ui/Toolbar.svelte';

    let shifts: any[] = $state([]);
    let loading = $state(true);
    let filterStatus = $state('all');

    const filteredShifts = $derived(
        filterStatus === 'all' 
            ? shifts 
            : shifts.filter(s => s.status === filterStatus)
    );

    onMount(async () => {
        try {
            shifts = await fetchApi('/api/v1/pos/sales/shifts/');
        } catch (e) {
            console.error("Error al cargar historial de turnos", e);
        } finally {
            loading = false;
        }
    });

    function getDuration(start: string, end: string | null) {
        if (!end) return 'En curso...';
        const s = new Date(start);
        const e = new Date(end);
        const diffMs = e.getTime() - s.getTime();
        const diffHrs = Math.floor(diffMs / (1000 * 60 * 60));
        const diffMins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
        return `${diffHrs}h ${diffMins}m`;
    }
</script>

<div class="p-6 lg:p-10 max-w-7xl mx-auto w-full space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
    
    <!-- Unified Header Toolbar -->
    <Toolbar title="Historial de Cortes">
        {#snippet left()}
            <a href="/admin" class="btn btn-ghost btn-sm font-black gap-1 rounded-xl uppercase tracking-wider text-xs">
                ← Volver al Panel
            </a>
        {/snippet}
        
        {#snippet right()}
            <div class="tabs tabs-boxed bg-base-200 p-1 rounded-xl shadow-inner flex items-center">
                <button 
                    class="tab tab-sm rounded-lg font-bold transition-all duration-200 {filterStatus === 'all' ? 'tab-active bg-primary text-primary-content shadow-md' : 'opacity-60'}" 
                    onclick={() => filterStatus = 'all'}>Todos</button>
                <button 
                    class="tab tab-sm rounded-lg font-bold transition-all duration-200 {filterStatus === 'OPEN' ? 'tab-active bg-primary text-primary-content shadow-md' : 'opacity-60'}" 
                    onclick={() => filterStatus = 'OPEN'}>Abiertos</button>
                <button 
                    class="tab tab-sm rounded-lg font-bold transition-all duration-200 {filterStatus === 'CLOSED' ? 'tab-active bg-primary text-primary-content shadow-md' : 'opacity-60'}" 
                    onclick={() => filterStatus = 'CLOSED'}>Cerrados</button>
            </div>
        {/snippet}
    </Toolbar>

    {#if loading}
        <div class="space-y-4">
            {#each Array(5) as _}
                <div class="h-20 bg-base-300 animate-pulse rounded-2xl"></div>
            {/each}
        </div>
    {:else}
        <div class="bg-base-100 border border-base-content/5 rounded-3xl overflow-hidden shadow-2xl">
            <div class="overflow-x-auto">
                <table class="table table-lg">
                    <thead>
                        <tr class="bg-base-200/50">
                            <th class="font-black text-xs uppercase tracking-widest">Turno ID</th>
                            <th class="font-black text-xs uppercase tracking-widest">Apertura / Cierre</th>
                            <th class="font-black text-xs uppercase tracking-widest text-center">Duración</th>
                            <th class="font-black text-xs uppercase tracking-widest text-right">Total Ventas</th>
                            <th class="font-black text-xs uppercase tracking-widest text-center">Órdenes</th>
                            <th class="font-black text-xs uppercase tracking-widest text-center">Diferencia</th>
                            <th class="font-black text-xs uppercase tracking-widest">Estado</th>
                            <th class="font-black text-xs uppercase tracking-widest"></th>
                        </tr>
                    </thead>
                    <tbody>
                        {#if filteredShifts.length === 0}
                            <tr>
                                <td colspan="8" class="text-center py-20">
                                    <div class="flex flex-col items-center gap-4 opacity-30">
                                        <svg xmlns="http://www.w3.org/2000/svg" class="w-16 h-16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                                        </svg>
                                        <p class="font-black text-xl">No se encontraron turnos</p>
                                    </div>
                                </td>
                            </tr>
                        {:else}
                            {#each filteredShifts as shift}
                                <tr class="hover:bg-base-200/50 transition-colors group">
                                    <td class="font-black text-primary text-xl">#{shift.id}</td>
                                    <td>
                                        <div class="flex flex-col">
                                            <div class="flex items-center gap-2">
                                                <div class="w-2 h-2 rounded-full bg-success/50"></div>
                                                <span class="font-black text-sm">{formatDateTime(shift.start_time)}</span>
                                            </div>
                                            {#if shift.end_time}
                                                <div class="flex items-center gap-2 mt-1">
                                                    <div class="w-2 h-2 rounded-full bg-error/50"></div>
                                                    <span class="font-black text-sm opacity-60">{formatDateTime(shift.end_time)}</span>
                                                </div>
                                            {:else}
                                                <div class="flex items-center gap-2 mt-1">
                                                    <div class="w-2 h-2 rounded-full bg-warning animate-pulse"></div>
                                                    <span class="font-black text-xs uppercase text-warning">Activo ahora</span>
                                                </div>
                                            {/if}
                                        </div>
                                    </td>
                                    <td class="text-center font-bold font-mono opacity-60">
                                        {getDuration(shift.start_time, shift.end_time)}
                                    </td>
                                    <td class="text-right font-black text-lg tabular-nums">
                                        {formatCurrency(shift.sales.total)}
                                    </td>
                                    <td class="text-center">
                                        <div class="badge badge-outline font-black">{shift.orders_count}</div>
                                    </td>
                                    <td class="text-center font-bold">
                                        {#if shift.status === 'CLOSED'}
                                            <span class="px-3 py-1 rounded-lg {shift.difference === 0 ? 'bg-success/10 text-success' : shift.difference > 0 ? 'bg-info/10 text-info' : 'bg-error/10 text-error'}">
                                                {shift.difference > 0 ? '+' : ''}{formatCurrency(shift.difference)}
                                            </span>
                                        {:else}
                                            <span class="opacity-20">—</span>
                                        {/if}
                                    </td>
                                    <td>
                                        {#if shift.status === 'OPEN'}
                                            <div class="badge badge-warning font-black p-3 uppercase text-[10px] tracking-widest">Abierto</div>
                                        {:else}
                                            <div class="badge badge-success font-black p-3 uppercase text-[10px] tracking-widest opacity-70">Cerrado</div>
                                        {/if}
                                    </td>
                                    <td class="text-right">
                                        <Button 
                                            variant="ghost" 
                                            size="sm" 
                                            onclick={() => goto(`/admin/shifts/${shift.id}`)}
                                            class="group-hover:bg-primary group-hover:text-primary-content font-black"
                                        >
                                            Ver Detalle
                                        </Button>
                                    </td>
                                </tr>
                            {/each}
                        {/if}
                    </tbody>
                </table>
            </div>
        </div>
    {/if}
</div>
