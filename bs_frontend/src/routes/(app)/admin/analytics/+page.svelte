<script lang="ts">
    import { onMount } from 'svelte';
    import { fetchApi } from '$lib/api';
    import { formatCurrency } from '$lib/utils';
    import Button from '$lib/components/ui/Button.svelte';

    type Period = 'today' | 'week' | 'month' | 'custom';
    let period: Period = $state('today');
    let fromDate: string = $state('');
    let toDate: string = $state('');
    
    let summary: any = $state(null);
    let error: string | null = $state(null);
    let loading = $state(true);

    onMount(async () => {
        await loadData();
    });

    async function loadData() {
        loading = true;
        error = null;
        try {
            let url = `/api/v1/pos/analytics/business-summary?period=${period}`;
            if (period === 'custom') {
                if (!fromDate || !toDate) {
                    summary = null;
                    loading = false;
                    return;
                }
                url += `&from_date=${fromDate}&to_date=${toDate}`;
            }
            summary = await fetchApi(url);
        } catch (e: any) {
            error = e.message;
        } finally {
            loading = false;
        }
    }

    // Reactividad
    $effect(() => {
        if (period !== 'custom') {
            loadData();
        }
    });

    function handleCustomSearch() {
        if (fromDate && toDate) {
            loadData();
        }
    }
</script>

<div class="p-6 lg:p-10 max-w-7xl mx-auto space-y-8 flex-1 min-h-0 overflow-y-auto w-full animate-in fade-in slide-in-from-bottom-4 duration-500">
    <!-- Header -->
    <header class="flex flex-col lg:flex-row lg:items-end justify-between gap-8">
        <div>
            <div class="text-sm breadcrumbs opacity-50 font-bold uppercase tracking-widest">
                <ul>
                    <li><a href="/admin">Admin</a></li>
                    <li>Analíticas</li>
                </ul>
            </div>
            <h1 class="text-5xl font-black text-base-content tracking-tighter uppercase">
                Ventas & <span class="text-primary">Desempeño</span>
            </h1>
            <p class="text-base-content/60 font-medium mt-1">Análisis detallado de transacciones y estados operativos</p>
        </div>

        <div class="flex flex-col gap-4">
            <div class="tabs tabs-boxed bg-base-300 p-1 rounded-2xl shadow-inner inline-flex">
                <button 
                    class="tab rounded-xl font-bold transition-all {period === 'today' ? 'tab-active bg-primary text-primary-content shadow-lg' : ''}" 
                    onclick={() => period = 'today'}>Hoy</button>
                <button 
                    class="tab rounded-xl font-bold transition-all {period === 'week' ? 'tab-active bg-primary text-primary-content shadow-lg' : ''}" 
                    onclick={() => period = 'week'}>Semana</button>
                <button 
                    class="tab rounded-xl font-bold transition-all {period === 'month' ? 'tab-active bg-primary text-primary-content shadow-lg' : ''}" 
                    onclick={() => period = 'month'}>Mes</button>
                <button 
                    class="tab rounded-xl font-bold transition-all {period === 'custom' ? 'tab-active bg-primary text-primary-content shadow-lg' : ''}" 
                    onclick={() => period = 'custom'}>Personalizado</button>
            </div>

            {#if period === 'custom'}
                <div class="flex items-end gap-2 p-4 bg-base-100 rounded-2xl border border-primary/20 shadow-xl animate-in fade-in zoom-in-95 duration-200">
                    <div class="form-control">
                        <label class="label p-0 mb-1"><span class="label-text-alt font-black uppercase tracking-widest opacity-40">De</span></label>
                        <input type="date" bind:value={fromDate} class="input input-bordered input-sm font-bold" />
                    </div>
                    <div class="form-control">
                        <label class="label p-0 mb-1"><span class="label-text-alt font-black uppercase tracking-widest opacity-40">Até</span></label>
                        <input type="date" bind:value={toDate} class="input input-bordered input-sm font-bold" />
                    </div>
                    <Button variant="primary" size="sm" class="font-black" onclick={handleCustomSearch}>Buscar</Button>
                </div>
            {/if}
        </div>
    </header>

    {#if loading}
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
            {#each Array(4) as _}
                <div class="h-32 bg-base-300 animate-pulse rounded-3xl"></div>
            {/each}
        </div>
    {:else if error}
        <div class="alert alert-error font-bold shadow-xl border-none text-error-content rounded-3xl">
            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            <span>Error cargando analíticas: {error}</span>
        </div>
    {:else if summary}
        <!-- KPI Row -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div class="card bg-base-100 shadow-xl border border-success/10 overflow-hidden">
                <div class="card-body p-6">
                    <span class="text-[10px] font-black uppercase tracking-widest opacity-40">Monto Total Vendido</span>
                    <h2 class="text-4xl font-black text-success tabular-nums">{formatCurrency(summary.total_sales)}</h2>
                    <p class="text-xs font-bold opacity-50 mt-1">{summary.total_payments} pagos registrados</p>
                </div>
            </div>

            <div class="card bg-base-100 shadow-xl border border-primary/10 overflow-hidden">
                <div class="card-body p-6">
                    <span class="text-[10px] font-black uppercase tracking-widest opacity-40">Tickets Totales</span>
                    <h2 class="text-4xl font-black text-primary tabular-nums">{summary.total_orders}</h2>
                    <p class="text-xs font-bold opacity-50 mt-1">Incluye cancelados y pendientes</p>
                </div>
            </div>

            <div class="card bg-base-100 shadow-xl border border-secondary/10 overflow-hidden">
                <div class="card-body p-6">
                    <span class="text-[10px] font-black uppercase tracking-widest opacity-40">Turnos de Caja</span>
                    <h2 class="text-4xl font-black text-secondary tabular-nums">{summary.closed_shifts_count}</h2>
                    <p class="text-xs font-bold opacity-50 mt-1">Completados en este período</p>
                </div>
            </div>

            <div class="card bg-base-100 shadow-xl border border-warning/10 overflow-hidden">
                <div class="card-body p-6">
                    <span class="text-[10px] font-black uppercase tracking-widest opacity-40">Ticket Promedio</span>
                    <h2 class="text-4xl font-black text-warning tabular-nums">
                        {summary.total_orders > 0 ? formatCurrency(summary.total_sales / summary.total_orders) : '$0.00'}
                    </h2>
                    <p class="text-xs font-bold opacity-50 mt-1">Eficiencia por orden</p>
                </div>
            </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <!-- Métodos de Pago -->
            <div class="card bg-base-100 shadow-xl border border-base-content/5">
                <div class="card-body p-8">
                    <h3 class="flex items-center gap-2 text-xl font-black uppercase tracking-tight mb-6">
                        <span class="w-1.5 h-6 bg-primary rounded-full"></span>
                        Métodos de Pago
                    </h3>
                    <div class="space-y-4">
                        {#each Object.entries(summary.by_payment_method) as [method, amount]}
                            <div class="flex justify-between items-center p-4 bg-base-200 rounded-2xl border border-base-300">
                                <div class="flex items-center gap-3">
                                    <div class="w-10 h-10 flex items-center justify-center bg-base-100 rounded-xl shadow-sm text-xl">
                                        {#if method === 'CASH'}💵{:else if method === 'CARD'}💳{:else}📲{/if}
                                    </div>
                                    <span class="font-black opacity-80">{method}</span>
                                </div>
                                <span class="font-black text-2xl tabular-nums">{formatCurrency(amount as number)}</span>
                            </div>
                        {:else}
                            <p class="text-center py-10 opacity-30 font-bold">Sin datos de pago.</p>
                        {/each}
                    </div>
                </div>
            </div>

            <!-- Top Productos -->
            <div class="card bg-base-100 shadow-xl border border-base-content/5 lg:col-span-2">
                <div class="card-body p-8">
                    <h3 class="flex items-center gap-2 text-xl font-black uppercase tracking-tight mb-6">
                        <span class="w-1.5 h-6 bg-secondary rounded-full"></span>
                        Productos más Vendidos
                    </h3>
                    <div class="overflow-x-auto">
                        <table class="table table-lg">
                            <thead>
                                <tr class="bg-base-200/50">
                                    <th class="font-black text-[10px] uppercase tracking-widest opacity-50">#</th>
                                    <th class="font-black text-[10px] uppercase tracking-widest opacity-50">Producto</th>
                                    <th class="font-black text-[10px] uppercase tracking-widest opacity-50 text-right">Cantidad</th>
                                </tr>
                            </thead>
                            <tbody>
                                {#each summary.top_products || [] as prod, i}
                                    <tr class="hover:bg-base-200/30 transition-colors">
                                        <td class="font-black opacity-20 text-3xl">{i + 1}</td>
                                        <td>
                                            <div class="font-black text-lg">{prod.name}</div>
                                            <div class="text-[10px] font-black uppercase tracking-widest opacity-30">ID: {prod.product_id}</div>
                                        </td>
                                        <td class="text-right">
                                            <div class="badge badge-secondary badge-lg font-black h-10 px-6 tabular-nums">
                                                {prod.quantity} unidades
                                            </div>
                                        </td>
                                    </tr>
                                {:else}
                                    <tr>
                                        <td colspan="3" class="text-center py-12 opacity-30 font-bold">No se encontraron productos vendidos en este período.</td>
                                    </tr>
                                {/each}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <!-- Estados de Órdenes -->
        <div class="card bg-base-300 shadow-inner">
            <div class="card-body p-8">
                <h3 class="text-sm font-black uppercase tracking-widest opacity-40 mb-6 text-center">Estado de las Órdenes en el Período</h3>
                <div class="flex flex-wrap justify-center gap-12">
                    {#each Object.entries(summary.orders_by_status) as [status, count]}
                        <div class="flex flex-col items-center">
                            <span class="text-5xl font-black mb-1 tabular-nums">{count}</span>
                            <div class="badge badge-outline font-black uppercase text-[10px] tracking-widest p-3 bg-base-100">
                                {status}
                            </div>
                        </div>
                    {/each}
                </div>
            </div>
        </div>
    {/if}
</div>

<style>
    .tab-active {
        color: var(--pc);
    }
</style>
