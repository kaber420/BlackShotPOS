<script lang="ts">
    import { onMount } from 'svelte';
    import { fetchApi } from '$lib/api';

    let stats: any = $state(null);
    let error: string | null = $state(null);
    let loading = $state(true);

    onMount(async () => {
        try {
            stats = await fetchApi('/api/v1/pos/analytics/dashboard');
        } catch (e: any) {
            error = e.message;
        } finally {
            loading = false;
        }
    });

    function formatL(amount: number) {
        return new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(amount);
    }
</script>

<div class="p-4 lg:p-8 max-w-7xl mx-auto space-y-8">
    <div class="flex items-center justify-between">
        <h1 class="text-4xl font-black text-primary flex items-center gap-3 tracking-tighter">
            📈 Panel de Analíticas
        </h1>
        <div class="text-sm font-bold opacity-50 uppercase tracking-widest">Resumen del Día</div>
    </div>

    {#if loading}
        <div class="flex justify-center py-12">
            <span class="loading loading-spinner loading-lg text-primary"></span>
        </div>
    {:else if error}
        <div class="alert alert-error font-bold">
            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            <span>Error cargando analíticas: {error}</span>
        </div>
    {:else if stats}
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <!-- Ventas Totales -->
            <div class="card bg-base-100 shadow-xl border border-base-200">
                <div class="card-body">
                    <h2 class="card-title text-base-content/50 uppercase text-xs font-black tracking-widest">Ventas de Hoy</h2>
                    <p class="text-5xl font-black text-success">{formatL(stats.sales_today)}</p>
                </div>
            </div>

            <!-- Órdenes Totales -->
            <div class="card bg-base-100 shadow-xl border border-base-200">
                <div class="card-body">
                    <h2 class="card-title text-base-content/50 uppercase text-xs font-black tracking-widest">Órdenes Procesadas</h2>
                    <p class="text-5xl font-black text-primary">{stats.orders_count}</p>
                </div>
            </div>

            <!-- Órdenes Canceladas -->
            <div class="card bg-base-100 shadow-xl border border-error/20">
                <div class="card-body">
                    <h2 class="card-title text-error/80 uppercase text-xs font-black tracking-widest">Cancelaciones</h2>
                    <p class="text-5xl font-black text-error">{stats.cancelled_count}</p>
                </div>
            </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-8">
            <div class="card bg-base-100 shadow-xl border border-base-200">
                <div class="card-body">
                    <h2 class="card-title text-xl font-black mb-4">Múltiples Métodos de Pago</h2>
                    {#if stats.payments_by_method && stats.payments_by_method.length > 0}
                        <div class="space-y-4">
                            {#each stats.payments_by_method as p}
                                <div class="flex justify-between items-center p-3 bg-base-200 rounded-xl">
                                    <span class="font-bold opacity-80">{p.method}</span>
                                    <span class="font-black text-xl">{formatL(p.total)}</span>
                                </div>
                            {/each}
                        </div>
                    {:else}
                        <p class="opacity-50 font-medium">No hay pagos registrados hoy.</p>
                    {/if}
                </div>
            </div>
        </div>
    {/if}
</div>
