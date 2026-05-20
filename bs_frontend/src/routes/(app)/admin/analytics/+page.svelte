<script lang="ts">
    import { onMount } from 'svelte';
    import { fetchApi } from '$lib/api';
    import { formatCurrency } from '$lib/utils';
    import Button from '$lib/components/ui/Button.svelte';
    import Toolbar from '$lib/components/ui/Toolbar.svelte';

    type Period = 'today' | 'week' | 'month' | 'custom';
    let period: Period = $state('today');
    let fromDate: string = $state('');
    let toDate: string = $state('');

    let summary: any = $state(null);
    let error: string | null = $state(null);
    let loading = $state(true);

    // ── Estadísticas de equipo (meseros y cocineros) ─────────────────────────────
    interface WaiterStat {
        waiter_uuid: string;
        waiter_name: string;
        orders_count: number;
        total_sales: number;
        avg_delivery_seconds: number | null;
    }
    interface CookStat {
        cook_uuid: string;
        cook_name: string;
        orders_handled: number;
        items_prepared: number;
        avg_prep_seconds: number | null;
    }
    interface DishSpeed {
        product_id: number;
        product_name: string;
        avg_prep_seconds: number;
        sample_count: number;
    }

    let waiterStats: WaiterStat[] = $state([]);
    let cookStats: CookStat[] = $state([]);
    let dishSpeed: DishSpeed[] = $state([]);
    let teamLoading = $state(true);

    onMount(async () => {
        await Promise.all([loadData(), loadTeamStats()]);
    });

    async function loadData() {
        loading = true;
        error = null;
        try {
            let url = `/api/v1/pos/system/analytics/business-summary?period=${period}`;
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

    async function loadTeamStats() {
        teamLoading = true;
        try {
            const [w, c, d] = await Promise.all([
                fetchApi('/api/v1/pos/system/analytics/waiters/performance'),
                fetchApi('/api/v1/pos/system/analytics/kitchen/performance'),
                fetchApi('/api/v1/pos/system/analytics/kitchen/dish-speed'),
            ]);
            waiterStats = w;
            cookStats = c;
            dishSpeed = d;
        } catch {
            // Silenciar si no hay datos todavía
        } finally {
            teamLoading = false;
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

    // Helpers de formato
    function formatSeconds(secs: number | null): string {
        if (secs === null || secs === undefined) return '—';
        const m = Math.floor(secs / 60);
        const s = Math.round(secs % 60);
        return m > 0 ? `${m}m ${s}s` : `${s}s`;
    }
    function deliveryBadge(secs: number | null) {
        if (secs === null) return { label: 'Sin datos', cls: 'badge-neutral' };
        if (secs < 120)  return { label: '🔥 Excelente',  cls: 'badge-success' };
        if (secs < 300)  return { label: '✅ Estándar',  cls: 'badge-warning' };
        return              { label: '⚠️ Por mejorar',   cls: 'badge-error' };
    }
    function prepBadge(secs: number | null) {
        if (secs === null) return { label: 'Sin datos', cls: 'badge-neutral' };
        if (secs < 300)  return { label: '⚡ Excelente',  cls: 'badge-success' };
        if (secs < 600)  return { label: '✅ Estándar',  cls: 'badge-warning' };
        return              { label: '⚠️ Por mejorar',   cls: 'badge-error' };
    }
</script>

<div class="p-6 lg:p-10 space-y-8 flex-1 min-h-0 overflow-y-auto w-full animate-in fade-in slide-in-from-bottom-4 duration-500">
    
    <!-- Unified Header Toolbar -->
    <Toolbar title="Ventas & Desempeño">
        {#snippet left()}
            <a href="/admin" class="btn btn-ghost btn-sm font-black gap-1 rounded-xl uppercase tracking-wider text-xs">
                ← Volver al Panel
            </a>
        {/snippet}
        
        {#snippet right()}
            <div class="flex flex-col sm:flex-row items-end sm:items-center gap-3">
                <div class="tabs tabs-boxed bg-base-200 p-1 rounded-xl shadow-inner flex items-center">
                    <button 
                        class="tab tab-sm rounded-lg font-bold transition-all duration-200 {period === 'today' ? 'tab-active bg-primary text-primary-content shadow-md' : 'opacity-60'}" 
                        onclick={() => period = 'today'}>Hoy</button>
                    <button 
                        class="tab tab-sm rounded-lg font-bold transition-all duration-200 {period === 'week' ? 'tab-active bg-primary text-primary-content shadow-md' : 'opacity-60'}" 
                        onclick={() => period = 'week'}>Semana</button>
                    <button 
                        class="tab tab-sm rounded-lg font-bold transition-all duration-200 {period === 'month' ? 'tab-active bg-primary text-primary-content shadow-md' : 'opacity-60'}" 
                        onclick={() => period = 'month'}>Mes</button>
                    <button 
                        class="tab tab-sm rounded-lg font-bold transition-all duration-200 {period === 'custom' ? 'tab-active bg-primary text-primary-content shadow-md' : 'opacity-60'}" 
                        onclick={() => period = 'custom'}>Personalizado</button>
                </div>

                {#if period === 'custom'}
                    <div class="flex items-end gap-2 p-2 bg-base-100 rounded-2xl border border-primary/20 shadow-xl animate-in fade-in zoom-in-95 duration-200">
                        <div class="form-control">
                            <input type="date" bind:value={fromDate} class="input input-bordered input-xs font-bold w-32" />
                        </div>
                        <div class="form-control">
                            <input type="date" bind:value={toDate} class="input input-bordered input-xs font-bold w-32" />
                        </div>
                        <Button variant="primary" size="xs" class="font-black" onclick={handleCustomSearch}>Buscar</Button>
                    </div>
                {/if}
            </div>
        {/snippet}
    </Toolbar>

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
        <!-- ════════════════════════════════════════════════════════
             SECCIÓN: DESEMPEÑO DE EQUIPO
        ════════════════════════════════════════════════════════ -->
        <div class="divider my-2"><span class="text-xs font-black uppercase tracking-widest opacity-30">Desempeño del Equipo — Hoy</span></div>

        {#if teamLoading}
            <div class="flex gap-4">
                {#each Array(3) as _}
                    <div class="h-48 flex-1 bg-base-300 animate-pulse rounded-3xl"></div>
                {/each}
            </div>
        {:else}
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">

                <!-- TABLA: Meseros -->
                <div class="card bg-base-100 shadow-xl border border-base-content/5">
                    <div class="card-body p-6">
                        <h3 class="flex items-center gap-2 text-lg font-black uppercase tracking-tight mb-4">
                            <span class="w-1.5 h-5 bg-info rounded-full"></span>
                            🤵 Meseros
                        </h3>
                        {#if waiterStats.length === 0}
                            <p class="text-center py-8 opacity-30 text-sm font-bold">No hay datos para hoy.<br>Las órdenes creadas aparecerán aquí.</p>
                        {:else}
                            <div class="overflow-x-auto">
                                <table class="table table-sm w-full">
                                    <thead>
                                        <tr class="bg-base-200/50">
                                            <th class="font-black text-[9px] uppercase tracking-widest opacity-50">#</th>
                                            <th class="font-black text-[9px] uppercase tracking-widest opacity-50">Nombre</th>
                                            <th class="font-black text-[9px] uppercase tracking-widest opacity-50 text-right">Tickets</th>
                                            <th class="font-black text-[9px] uppercase tracking-widest opacity-50 text-right">Ventas</th>
                                            <th class="font-black text-[9px] uppercase tracking-widest opacity-50 text-center">Entrega</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {#each waiterStats as stat, i}
                                            {@const badge = deliveryBadge(stat.avg_delivery_seconds)}
                                            <tr class="hover:bg-base-200/30 transition-colors {i === 0 ? 'font-black' : ''}">
                                                <td class="opacity-30 font-black text-xl">{i + 1}</td>
                                                <td class="font-bold">
                                                    {stat.waiter_name}
                                                    {#if i === 0}<span class="ml-1 text-xs">🏆</span>{/if}
                                                </td>
                                                <td class="text-right tabular-nums font-bold text-primary">{stat.orders_count}</td>
                                                <td class="text-right tabular-nums font-bold text-success">{formatCurrency(stat.total_sales)}</td>
                                                <td class="text-center">
                                                    <span class="badge {badge.cls} badge-sm font-black text-white">
                                                        {formatSeconds(stat.avg_delivery_seconds)}
                                                    </span>
                                                </td>
                                            </tr>
                                        {/each}
                                    </tbody>
                                </table>
                            </div>
                        {/if}
                    </div>
                </div>

                <!-- TABLA: Cocineros -->
                <div class="card bg-base-100 shadow-xl border border-base-content/5">
                    <div class="card-body p-6">
                        <h3 class="flex items-center gap-2 text-lg font-black uppercase tracking-tight mb-4">
                            <span class="w-1.5 h-5 bg-warning rounded-full"></span>
                            👨‍🍳 Cocina
                        </h3>
                        {#if cookStats.length === 0}
                            <p class="text-center py-8 opacity-30 text-sm font-bold">No hay datos para hoy.<br>Las órdenes preparadas aparecerán aquí.</p>
                        {:else}
                            <div class="overflow-x-auto">
                                <table class="table table-sm w-full">
                                    <thead>
                                        <tr class="bg-base-200/50">
                                            <th class="font-black text-[9px] uppercase tracking-widest opacity-50">#</th>
                                            <th class="font-black text-[9px] uppercase tracking-widest opacity-50">Cocinero</th>
                                            <th class="font-black text-[9px] uppercase tracking-widest opacity-50 text-right">Órdenes</th>
                                            <th class="font-black text-[9px] uppercase tracking-widest opacity-50 text-right">Items</th>
                                            <th class="font-black text-[9px] uppercase tracking-widest opacity-50 text-center">Prep.</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {#each cookStats as stat, i}
                                            {@const badge = prepBadge(stat.avg_prep_seconds)}
                                            <tr class="hover:bg-base-200/30 transition-colors {i === 0 ? 'font-black' : ''}">
                                                <td class="opacity-30 font-black text-xl">{i + 1}</td>
                                                <td class="font-bold">
                                                    {stat.cook_name}
                                                    {#if i === 0}<span class="ml-1 text-xs">🏆</span>{/if}
                                                </td>
                                                <td class="text-right tabular-nums font-bold text-primary">{stat.orders_handled}</td>
                                                <td class="text-right tabular-nums font-bold opacity-60">{stat.items_prepared}</td>
                                                <td class="text-center">
                                                    <span class="badge {badge.cls} badge-sm font-black text-white">
                                                        {formatSeconds(stat.avg_prep_seconds)}
                                                    </span>
                                                </td>
                                            </tr>
                                        {/each}
                                    </tbody>
                                </table>
                            </div>
                        {/if}
                    </div>
                </div>

                <!-- TABLA: Velocidad por Platillo -->
                <div class="card bg-base-100 shadow-xl border border-base-content/5">
                    <div class="card-body p-6">
                        <h3 class="flex items-center gap-2 text-lg font-black uppercase tracking-tight mb-4">
                            <span class="w-1.5 h-5 bg-secondary rounded-full"></span>
                            ⏱️ Velocidad por Platillo
                        </h3>
                        {#if dishSpeed.length === 0}
                            <p class="text-center py-8 opacity-30 text-sm font-bold">Datos acumulados aparecerán<br>cuando se registren preparaciones por ítem.</p>
                        {:else}
                            <div class="overflow-x-auto">
                                <table class="table table-sm w-full">
                                    <thead>
                                        <tr class="bg-base-200/50">
                                            <th class="font-black text-[9px] uppercase tracking-widest opacity-50">#</th>
                                            <th class="font-black text-[9px] uppercase tracking-widest opacity-50">Platillo</th>
                                            <th class="font-black text-[9px] uppercase tracking-widest opacity-50 text-right">Prom.</th>
                                            <th class="font-black text-[9px] uppercase tracking-widest opacity-50 text-center">Velocidad</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {#each dishSpeed as dish, i}
                                            {@const badge = prepBadge(dish.avg_prep_seconds)}
                                            <tr class="hover:bg-base-200/30 transition-colors">
                                                <td class="opacity-30 font-black text-xl">{i + 1}</td>
                                                <td class="font-bold">
                                                    {dish.product_name}
                                                    <div class="text-[9px] font-bold opacity-30">{dish.sample_count} pedidos</div>
                                                </td>
                                                <td class="text-right tabular-nums font-bold opacity-70">{formatSeconds(dish.avg_prep_seconds)}</td>
                                                <td class="text-center">
                                                    <span class="badge {badge.cls} badge-sm font-black text-white">{badge.label}</span>
                                                </td>
                                            </tr>
                                        {/each}
                                    </tbody>
                                </table>
                            </div>
                        {/if}
                    </div>
                </div>

            </div><!-- end grid equipo -->
        {/if}<!-- end teamLoading -->
    {/if}<!-- end summary -->
</div>

<style>
    .tab-active {
        color: var(--pc);
    }
</style>
