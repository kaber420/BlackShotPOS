<script lang="ts">
    import { onMount } from 'svelte';
    import { fetchApi } from '$lib/api';
    import Button from '$lib/components/ui/Button.svelte';
    import { appState, can } from '$lib/app_state.svelte';
    import { formatCurrency, formatDate, formatDateTime } from '$lib/utils';
    import Toolbar from '$lib/components/ui/Toolbar.svelte';
    
    type Period = 'today' | 'week' | 'month';
    let period: Period = $state('today');
    let summary: any = $state(null);
    let recentShifts: any[] = $state([]);
    let loading = $state(true);

    onMount(async () => {
        await loadData();
    });

    async function loadData() {
        loading = true;
        try {
            const [summaryRes, shiftsRes] = await Promise.all([
                fetchApi(`/api/v1/pos/system/analytics/business-summary?period=${period}`),
                fetchApi('/api/v1/pos/sales/shifts/'),
            ]);
            summary = summaryRes;
            // Solo mostrar los últimos 5
            recentShifts = Array.isArray(shiftsRes) ? shiftsRes.slice(0, 5) : [];
        } catch (e) {
            console.error("Error al cargar datos del dashboard", e);
        } finally {
            loading = false;
        }
    }

    // Reactividad para recargar cuando cambie el período
    $effect(() => {
        if (period) {
            loadData();
        }
    });

    const adminNavLinks = [
        { 
            name: 'Cortes', 
            href: '/admin/shifts',
            icon: '📋', 
            show: can.viewReports()
        },
        { 
            name: 'Cajas', 
            href: '/admin/registers', 
            icon: '🖥️', 
            show: can.manageShifts()
        },
        { 
            name: 'Analíticas', 
            href: '/admin/analytics', 
            icon: '📈', 
            show: can.viewReports()
        },
        { 
            name: 'Clientes', 
            href: '/admin/customers', 
            icon: '☕', 
            show: can.takeOrders()
        },
        { 
            name: 'Auditoría', 
            href: '/admin/audits', 
            icon: '🛡️', 
            show: can.viewReports()
        },
        { 
            name: 'Personal', 
            href: '/admin/users', 
            icon: '👥', 
            show: can.manageUsers()
        }
    ].filter(link => link.show);

    let paymentBreakdown = $derived(
        summary && summary.by_payment_method ? [
            { key: 'CASH', name: 'Efectivo', icon: '💵', color: 'bg-success', textClass: 'text-success', bgClass: 'bg-success/10', amount: summary.by_payment_method.CASH || 0 },
            { key: 'CARD', name: 'Tarjeta', icon: '💳', color: 'bg-info', textClass: 'text-info', bgClass: 'bg-info/10', amount: summary.by_payment_method.CARD || 0 },
            { key: 'TRANSFER', name: 'Transferencia', icon: '📲', color: 'bg-primary', textClass: 'text-primary', bgClass: 'bg-primary/10', amount: summary.by_payment_method.TRANSFER || 0 }
        ].map(item => ({
            ...item,
            percentage: summary.total_sales > 0 ? (item.amount / summary.total_sales) * 100 : 0
        })).sort((a, b) => b.amount - a.amount) : []
    );


</script>

<div class="p-6 lg:p-10 w-full space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
    
    <!-- Header Toolbar -->
    <Toolbar title="Administración">
        {#snippet left()}
            <div class="hidden md:flex items-center gap-1 ml-2">
                {#each adminNavLinks as link}
                    <a 
                        href={link.href} 
                        class="btn btn-ghost btn-sm font-black normal-case gap-1.5 rounded-xl px-3 text-base-content/70 hover:text-primary hover:bg-primary/10 transition-all duration-200"
                    >
                        <span>{link.icon}</span>
                        <span>{link.name}</span>
                    </a>
                {/each}
            </div>
        {/snippet}
        {#snippet right()}
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
            </div>
        {/snippet}
    </Toolbar>

    {#if loading && !summary}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {#each Array(4) as _}
                <div class="h-32 bg-base-300 animate-pulse rounded-3xl"></div>
            {/each}
        </div>
        <div class="h-64 bg-base-300 animate-pulse rounded-3xl"></div>
    {:else if summary}
        <!-- KPI Cards -->
        <section class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div class="card bg-base-100 shadow-xl border border-success/10 overflow-hidden group hover:shadow-success/5 transition-all duration-300">
                <div class="card-body p-6">
                    <div class="flex justify-between items-start">
                        <div class="p-3 bg-success/10 rounded-2xl text-success animate-bounce duration-1000">
                            <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </div>
                        <span class="text-xs font-black uppercase tracking-widest text-success/50">Ventas ({period})</span>
                    </div>
                    <div class="mt-4">
                        <h2 class="text-3xl font-black text-base-content tabular-nums">{formatCurrency(summary.total_sales)}</h2>
                        <p class="text-sm font-bold text-success/60 mt-1">{summary.total_payments} cobros realizados</p>
                    </div>
                </div>
            </div>

            <div class="card bg-base-100 shadow-xl border border-info/10 overflow-hidden group hover:shadow-info/5 transition-all duration-300">
                <div class="card-body p-6">
                    <div class="flex justify-between items-start">
                        <div class="p-3 bg-info/10 rounded-2xl text-info">
                            <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                            </svg>
                        </div>
                        <span class="text-xs font-black uppercase tracking-widest text-info/50">Órdenes</span>
                    </div>
                    <div class="mt-4">
                        <h2 class="text-3xl font-black text-base-content tabular-nums">{summary.total_orders}</h2>
                        <p class="text-sm font-bold text-info/60 mt-1">Total de tickets creados</p>
                    </div>
                </div>
            </div>

            <div class="card bg-base-100 shadow-xl border border-secondary/10 overflow-hidden group hover:shadow-secondary/5 transition-all duration-300">
                <div class="card-body p-6">
                    <div class="flex justify-between items-start">
                        <div class="p-3 bg-secondary/10 rounded-2xl text-secondary">
                            <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </div>
                        <span class="text-xs font-black uppercase tracking-widest text-secondary/50">Cortes Cerrados</span>
                    </div>
                    <div class="mt-4">
                        <h2 class="text-3xl font-black text-base-content tabular-nums">{summary.closed_shifts_count}</h2>
                        <p class="text-sm font-bold text-secondary/60 mt-1">Turnos de caja completados</p>
                    </div>
                </div>
            </div>

            <div class="card bg-base-100 shadow-xl border border-error/10 overflow-hidden group hover:shadow-error/5 transition-all duration-300">
                <div class="card-body p-6">
                    <div class="flex justify-between items-start">
                        <div class="p-3 bg-error/10 rounded-2xl text-error">
                            <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </div>
                        <span class="text-xs font-black uppercase tracking-widest text-error/50">Cancelaciones</span>
                    </div>
                    <div class="mt-4">
                        <h2 class="text-3xl font-black text-base-content tabular-nums">{summary.orders_by_status.CANCELLED || 0}</h2>
                        <p class="text-sm font-bold text-error/60 mt-1">Órdenes no concretadas</p>
                    </div>
                </div>
            </div>
        </section>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <!-- Recent Shifts Preview (Left Column) -->
            <section class="lg:col-span-2 space-y-4 order-2 lg:order-1">
                <div class="flex items-center justify-between">
                    <h3 class="text-xl font-black uppercase tracking-tight flex items-center gap-2">
                        <span class="w-1.5 h-6 bg-secondary rounded-full"></span>
                        Últimos Cortes de Caja
                    </h3>
                    <a href="/admin/shifts" class="btn btn-ghost btn-sm text-primary font-black uppercase tracking-wider text-xs rounded-xl hover:bg-primary/10 transition-all">Ver Todo</a>
                </div>
                
                <div class="bg-base-100 border border-base-content/5 rounded-3xl overflow-hidden shadow-xl hover:shadow-2xl transition-all duration-300">
                    <div class="overflow-x-auto">
                        <table class="table table-lg">
                            <thead>
                                <tr class="bg-base-200/50">
                                    <th class="font-black text-xs uppercase tracking-widest">ID</th>
                                    <th class="font-black text-xs uppercase tracking-widest">Fecha / Hora</th>
                                    <th class="font-black text-xs uppercase tracking-widest text-right">Ventas</th>
                                    <th class="font-black text-xs uppercase tracking-widest text-center">Diferencia</th>
                                    <th class="font-black text-xs uppercase tracking-widest">Estado</th>
                                </tr>
                            </thead>
                            <tbody>
                                {#if recentShifts.length === 0}
                                    <tr>
                                        <td colspan="5" class="text-center py-14 opacity-40 font-bold">No hay turnos registrados aún.</td>
                                    </tr>
                                {:else}
                                    {#each recentShifts as shift}
                                        <tr 
                                            class="hover:bg-base-200/50 transition-colors cursor-pointer" 
                                            onclick={() => window.location.href = `/admin/shifts/${shift.id}`}
                                        >
                                            <td class="font-black text-primary">#{shift.id}</td>
                                            <td>
                                                <div class="font-black text-sm">{formatDate(shift.start_time)}</div>
                                                <div class="text-[10px] opacity-50 uppercase font-black">{formatDateTime(shift.start_time).split(',')[1]}</div>
                                            </td>
                                            <td class="text-right font-black tabular-nums">{formatCurrency(shift.sales.total)}</td>
                                            <td class="text-center font-bold">
                                                {#if shift.status === 'CLOSED'}
                                                    <span class={shift.difference === 0 ? 'text-success' : shift.difference > 0 ? 'text-info' : 'text-error'}>
                                                        {shift.difference > 0 ? '+' : ''}{formatCurrency(shift.difference)}
                                                    </span>
                                                {:else}
                                                    <span class="opacity-30">—</span>
                                                {/if}
                                            </td>
                                            <td>
                                                {#if shift.status === 'OPEN'}
                                                    <div class="badge badge-warning badge-sm font-black gap-1 p-3">
                                                        <span class="w-1.5 h-1.5 bg-yellow-600 rounded-full animate-pulse"></span>
                                                        ABIERTO
                                                    </div>
                                                {:else}
                                                    <div class="badge badge-success badge-sm font-black gap-1 p-3">
                                                        <svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3" viewBox="0 0 20 20" fill="currentColor">
                                                            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                                                        </svg>
                                                        CERRADO
                                                    </div>
                                                {/if}
                                            </td>
                                        </tr>
                                    {/each}
                                {/if}
                            </tbody>
                        </table>
                    </div>
                </div>
            </section>

            <!-- Widgets Column (Right Column) -->
            <div class="lg:col-span-1 space-y-8 order-1 lg:order-2">
                <!-- Widget: Top Products -->
                <section class="bg-base-100 border border-base-content/5 rounded-3xl p-6 shadow-xl space-y-6 hover:shadow-2xl transition-all duration-300">
                    <div class="flex items-center justify-between border-b border-base-content/5 pb-4">
                        <div class="flex items-center gap-3">
                            <div class="w-10 h-10 rounded-xl bg-secondary/10 flex items-center justify-center text-secondary text-lg">
                                🏆
                            </div>
                            <div>
                                <h3 class="font-black text-sm uppercase tracking-wider text-base-content">Más Vendidos</h3>
                                <p class="text-[10px] font-semibold text-base-content/55">Top del período</p>
                            </div>
                        </div>
                    </div>

                    <div class="space-y-4">
                        {#if !summary.top_products || summary.top_products.length === 0}
                            <div class="py-8 text-center text-base-content/40 text-xs font-bold">
                                No hay datos de ventas.
                            </div>
                        {:else}
                            {@const maxQty = Math.max(...summary.top_products.map((p: any) => p.quantity), 1)}
                            {#each summary.top_products.slice(0, 5) as product, index}
                                {@const percentage = (product.quantity / maxQty) * 100}
                                <div class="space-y-1.5 group">
                                    <div class="flex justify-between items-center text-xs">
                                        <div class="flex items-center gap-2 font-black text-base-content/95 truncate">
                                            <span class="w-5 h-5 rounded-md bg-base-200 flex items-center justify-center text-[10px] text-base-content/60 group-hover:bg-primary group-hover:text-primary-content transition-colors font-serif">
                                                {index + 1}
                                            </span>
                                            <span class="truncate">{product.name}</span>
                                        </div>
                                        <span class="font-bold text-base-content/60 tabular-nums">{product.quantity} uds</span>
                                    </div>
                                    <div class="w-full bg-base-200 rounded-full h-2.5 overflow-hidden">
                                        <div 
                                            class="bg-gradient-to-r from-secondary to-primary h-full rounded-full transition-all duration-1000 ease-out" 
                                            style="width: {percentage}%"
                                        ></div>
                                    </div>
                                </div>
                            {/each}
                        {/if}
                    </div>
                </section>

                <!-- Widget: Payment Methods -->
                <section class="bg-base-100 border border-base-content/5 rounded-3xl p-6 shadow-xl space-y-6 hover:shadow-2xl transition-all duration-300">
                    <div class="flex items-center justify-between border-b border-base-content/5 pb-4">
                        <div class="flex items-center gap-3">
                            <div class="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary text-lg">
                                📊
                            </div>
                            <div>
                                <h3 class="font-black text-sm uppercase tracking-wider text-base-content">Métodos de Pago</h3>
                                <p class="text-[10px] font-semibold text-base-content/55">Distribución de ingresos</p>
                            </div>
                        </div>
                    </div>

                    <div class="space-y-4">
                        {#if paymentBreakdown.length === 0 || summary.total_sales === 0}
                            <div class="py-8 text-center text-base-content/40 text-xs font-bold">
                                Sin transacciones registradas.
                            </div>
                        {:else}
                            {#each paymentBreakdown as method}
                                <div class="space-y-1.5">
                                    <div class="flex justify-between items-center text-xs">
                                        <div class="flex items-center gap-2 font-black text-base-content/95">
                                            <span class="w-8 h-8 rounded-lg flex items-center justify-center text-md {method.bgClass} {method.textClass}">
                                                {method.icon}
                                            </span>
                                            <span>{method.name}</span>
                                        </div>
                                        <div class="text-right">
                                            <span class="font-black text-base-content/95 block tabular-nums">{formatCurrency(method.amount)}</span>
                                            <span class="text-[9px] font-bold opacity-50 block tabular-nums">{method.percentage.toFixed(1)}%</span>
                                        </div>
                                    </div>
                                    <div class="w-full bg-base-200 rounded-full h-2.5 overflow-hidden">
                                        <div 
                                            class="{method.color} h-full rounded-full transition-all duration-1000 ease-out" 
                                            style="width: {method.percentage}%"
                                        ></div>
                                    </div>
                                </div>
                            {/each}
                        {/if}
                    </div>
                </section>
            </div>
        </div>
    {/if}
</div>

<style>
    .tab-active {
        color: var(--pc);
    }
</style>
