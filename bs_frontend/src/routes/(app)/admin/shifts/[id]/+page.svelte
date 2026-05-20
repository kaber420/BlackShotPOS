<script lang="ts">
    import { page } from '$app/state';
    import { fetchApi } from '$lib/api';
    import { onMount } from 'svelte';
    import { formatCurrency, formatDateTime } from '$lib/utils';
    import Button from '$lib/components/ui/Button.svelte';
    import { goto } from '$app/navigation';
    import { can } from '$lib/app_state.svelte';

    let report: any = $state(null);
    let audits: any[] = $state([]);
    let loading = $state(true);
    let expandedOrders = $state<Record<number, boolean>>({});
    const shiftId = $derived(Number(page.params.id));

    // Filtro de logs de auditoría para este turno
    const shiftAudits = $derived(
        report && report.shift
            ? audits.filter((a: any) => {
                const ts = new Date(a.timestamp).getTime();
                const start = new Date(report.shift.start_time).getTime();
                const end = report.shift.end_time 
                    ? new Date(report.shift.end_time).getTime()
                    : Date.now();
                return ts >= start && ts <= end;
            })
            : []
    );

    function toggleOrder(id: number) {
        expandedOrders[id] = !expandedOrders[id];
    }

    onMount(async () => {
        try {
            report = await fetchApi(`/api/v1/pos/sales/shifts/${shiftId}/report`);
            
            // Si el usuario tiene permisos para ver auditorías, cargamos los logs del sistema
            if (can.viewReports()) {
                try {
                    audits = await fetchApi('/api/v1/pos/system/audit/audits');
                } catch (auditErr) {
                    console.error("No se pudieron cargar los logs de auditoría", auditErr);
                }
            }
        } catch (e) {
            console.error("Error al cargar reporte de turno", e);
        } finally {
            loading = false;
        }
    });

    function printReport() {
        window.print();
    }
</script>

<div class="p-6 lg:p-10 max-w-5xl mx-auto w-full space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 print:p-0 print:max-w-none">
    
    <!-- Header -->
    <header class="flex flex-col md:flex-row md:items-center justify-between gap-6 print:hidden">
        <div class="space-y-1">
            <div class="text-sm breadcrumbs opacity-50 font-bold uppercase tracking-widest">
                <ul>
                    <li><a href="/admin">Admin</a></li>
                    <li><a href="/admin/shifts">Cortes</a></li>
                    <li>#{shiftId}</li>
                </ul>
            </div>
            <h1 class="text-4xl font-black tracking-tight text-base-content uppercase">
                Detalle de <span class="text-primary">Corte #{shiftId}</span>
            </h1>
        </div>

        <div class="flex gap-3">
            <Button variant="ghost" onclick={() => goto('/admin/shifts')} class="font-bold">Regresar</Button>
            <Button variant="primary" onclick={printReport} class="font-black gap-2">
                <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
                </svg>
                Imprimir Reporte
            </Button>
        </div>
    </header>

    {#if loading}
        <div class="animate-pulse space-y-8">
            <div class="h-40 bg-base-300 rounded-3xl"></div>
            <div class="h-96 bg-base-300 rounded-3xl"></div>
        </div>
    {:else if report}
        <!-- Información General -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="md:col-span-2 card bg-base-100 border border-base-content/5 shadow-xl overflow-hidden">
                <div class="card-body p-8">
                    <h3 class="font-black uppercase tracking-widest text-xs opacity-50 mb-6 flex items-center gap-2">
                        <span class="w-1.5 h-4 bg-primary rounded-full"></span>
                        Resumen del Corte
                    </h3>
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-8">
                        <div>
                            <span class="text-[10px] font-black uppercase tracking-widest opacity-40 block mb-1">Apertura</span>
                            <p class="font-black text-lg">{formatDateTime(report.shift.start_time)}</p>
                        </div>
                        <div>
                            <span class="text-[10px] font-black uppercase tracking-widest opacity-40 block mb-1">Cierre</span>
                            {#if report.shift.end_time}
                                <p class="font-black text-lg">{formatDateTime(report.shift.end_time)}</p>
                            {:else}
                                <div class="badge badge-warning font-black uppercase text-[10px] mt-1">Abierto actualmente</div>
                            {/if}
                        </div>
                        <div>
                            <span class="text-[10px] font-black uppercase tracking-widest opacity-40 block mb-1">Estado de Caja</span>
                            <div class="flex items-center gap-3 mt-1">
                                <span class="font-black text-2xl {report.shift.difference === 0 ? 'text-success' : report.shift.difference > 0 ? 'text-info' : 'text-error'}">
                                    {report.shift.difference === 0 ? '✔️ Balanceado' : report.shift.difference > 0 ? '📈 Sobrante' : '📉 Faltante'}
                                </span>
                            </div>
                        </div>
                        <div>
                            <span class="text-[10px] font-black uppercase tracking-widest opacity-40 block mb-1">Ventas Totales</span>
                            <p class="font-black text-3xl tabular-nums text-primary">{formatCurrency(report.sales.total)}</p>
                        </div>
                    </div>
                </div>
            </div>

            <div class="card bg-base-100 border border-base-content/5 shadow-xl overflow-hidden">
                <div class="card-body p-8 bg-base-200/50">
                    <h3 class="font-black uppercase tracking-widest text-xs opacity-50 mb-6">Conciliación</h3>
                    <div class="space-y-4 font-bold">
                        <div class="flex justify-between text-base-content/60">
                            <span>Fondo Inicial</span>
                            <span>{formatCurrency(report.shift.initial_cash)}</span>
                        </div>
                        <div class="flex justify-between text-success">
                            <span>Ventas Efectivo</span>
                            <span>+ {formatCurrency(report.sales.cash || 0)}</span>
                        </div>
                        <div class="divider my-1"></div>
                        <div class="flex justify-between text-xl font-black">
                            <span>Esperado</span>
                            <span>{formatCurrency(report.shift.expected_cash)}</span>
                        </div>
                        <div class="flex justify-between text-xl font-black border-2 border-primary/20 p-2 rounded-xl bg-primary/5">
                            <span>Contado</span>
                            <span>{formatCurrency(report.shift.actual_cash || 0)}</span>
                        </div>
                        <div class="flex justify-between pt-2 {report.shift.difference < 0 ? 'text-error animate-pulse' : report.shift.difference > 0 ? 'text-info' : 'text-success'}">
                            <span>Diferencia</span>
                            <span>{report.shift.difference > 0 ? '+' : ''}{formatCurrency(report.shift.difference || 0)}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Métodos de Pago Tab -->
        <div class="card bg-base-100 border border-base-content/5 shadow-xl overflow-hidden">
            <div class="card-body p-8">
                <h3 class="font-black uppercase tracking-widest text-xs opacity-50 mb-6">Ventas por Método</h3>
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-6">
                    <div class="p-4 bg-base-200 rounded-2xl border border-base-300">
                        <span class="text-[10px] font-black uppercase tracking-widest opacity-40 block mb-2">💵 Efectivo</span>
                        <p class="font-black text-2xl tabular-nums">{formatCurrency(report.sales.cash || 0)}</p>
                    </div>
                    <div class="p-4 bg-base-200 rounded-2xl border border-base-300">
                        <span class="text-[10px] font-black uppercase tracking-widest opacity-40 block mb-2">💳 Tarjeta</span>
                        <p class="font-black text-2xl tabular-nums">{formatCurrency(report.sales.card || 0)}</p>
                    </div>
                    <div class="p-4 bg-base-200 rounded-2xl border border-base-300">
                        <span class="text-[10px] font-black uppercase tracking-widest opacity-40 block mb-2">📲 Transferencia</span>
                        <p class="font-black text-2xl tabular-nums">{formatCurrency(report.sales.transfer || 0)}</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Lista de Órdenes -->
        {#if report.expense_summary && report.expense_summary.length > 0}
            {@const totalExpenses = report.expense_summary.reduce((sum, e) => sum + e.total, 0)}
            <div class="card bg-base-100 border border-base-content/5 shadow-xl overflow-hidden">
                <div class="card-body p-8">
                    <h3 class="font-black uppercase tracking-widest text-xs opacity-50 mb-6 flex items-center gap-2">
                        <span class="w-1.5 h-4 bg-error rounded-full"></span>
                        Desglose de Gastos por Categoría
                    </h3>
                    <div class="flex items-baseline gap-3 mb-6">
                        <span class="text-3xl font-black text-error tabular-nums">{formatCurrency(totalExpenses)}</span>
                        <span class="text-xs font-bold uppercase tracking-widest opacity-40">Total egresos</span>
                    </div>
                    <div class="space-y-4">
                        {#each report.expense_summary as item}
                            {@const pct = totalExpenses > 0 ? (item.total / totalExpenses) * 100 : 0}
                            <div class="space-y-1.5">
                                <div class="flex items-center justify-between">
                                    <div class="flex items-center gap-2">
                                        <span class="font-black text-sm">{item.category}</span>
                                        <span class="badge badge-ghost badge-sm font-bold text-[9px]">{item.count} mov.</span>
                                    </div>
                                    <div class="flex items-center gap-3">
                                        <span class="text-[10px] font-black uppercase tracking-widest opacity-40">{pct.toFixed(0)}%</span>
                                        <span class="font-black tabular-nums text-error">{formatCurrency(item.total)}</span>
                                    </div>
                                </div>
                                <div class="w-full bg-base-200 rounded-full h-2.5 overflow-hidden">
                                    <div 
                                        class="bg-error/70 h-2.5 rounded-full transition-all duration-700"
                                        style="width: {pct}%"
                                    ></div>
                                </div>
                            </div>
                        {/each}
                    </div>
                </div>
            </div>
        {/if}

        <!-- Movimientos de Caja -->
        {#if report.movements && report.movements.length > 0}
            <div class="card bg-base-100 border border-base-content/5 shadow-xl overflow-hidden">
                <div class="card-body p-8">
                    <h3 class="font-black uppercase tracking-widest text-xs opacity-50 mb-6 flex items-center gap-2">
                        <span class="w-1.5 h-4 bg-warning rounded-full"></span>
                        Movimientos de Caja ({report.movements.length})
                    </h3>
                    <div class="overflow-x-auto">
                        <table class="table table-md">
                            <thead>
                                <tr class="bg-base-200/50">
                                    <th class="font-black uppercase text-[10px] tracking-widest">Hora</th>
                                    <th class="font-black uppercase text-[10px] tracking-widest">Concepto</th>
                                    <th class="font-black uppercase text-[10px] tracking-widest">Categoría</th>
                                    <th class="font-black uppercase text-[10px] tracking-widest">Registrado por</th>
                                    <th class="font-black uppercase text-[10px] tracking-widest">Tipo</th>
                                    <th class="font-black uppercase text-[10px] tracking-widest text-right">Monto</th>
                                </tr>
                            </thead>
                            <tbody>
                                {#each report.movements as mov}
                                    <tr class="hover:bg-base-200/50 transition-colors">
                                        <td class="font-bold opacity-50 tabular-nums">{new Date(mov.timestamp).toLocaleTimeString()}</td>
                                        <td class="font-black">{mov.reason}</td>
                                        <td>
                                            {#if mov.category_name}
                                                <span class="badge badge-ghost font-bold text-[10px] uppercase">{mov.category_name}</span>
                                            {:else}
                                                <span class="opacity-20 text-xs">—</span>
                                            {/if}
                                        </td>
                                        <td class="font-bold opacity-60">{mov.actor_name || '—'}</td>
                                        <td>
                                            <span class="badge {mov.type === 'INCOME' ? 'badge-success' : mov.type === 'WITHDRAWAL' ? 'badge-info' : 'badge-error'} font-black text-[10px] uppercase">
                                                {mov.type === 'INCOME' ? 'Entrada' : mov.type === 'WITHDRAWAL' ? 'Retiro' : 'Salida'}
                                            </span>
                                        </td>
                                        <td class="text-right font-black tabular-nums {mov.type === 'INCOME' ? 'text-success' : 'text-error'}">
                                            {mov.type === 'INCOME' ? '+' : '-'}{formatCurrency(mov.amount)}
                                        </td>
                                    </tr>
                                {/each}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        {/if}
        <div class="card bg-base-100 border border-base-content/5 shadow-2xl overflow-hidden print:shadow-none print:border-none">
            <div class="card-body p-8">
                <div class="flex items-center justify-between mb-6">
                    <h3 class="font-black uppercase tracking-widest text-xs opacity-50">Registro de Órdenes ({report.orders.length})</h3>
                </div>
                <div class="overflow-x-auto">
                    <table class="table table-md">
                        <thead>
                            <tr class="bg-base-200/50">
                                <th class="w-10 print:hidden"></th>
                                <th class="font-black uppercase text-[10px] tracking-widest">Ticket</th>
                                <th class="font-black uppercase text-[10px] tracking-widest">Hora</th>
                                <th class="font-black uppercase text-[10px] tracking-widest">Mesero</th>
                                <th class="font-black uppercase text-[10px] tracking-widest">Tipo</th>
                                <th class="font-black uppercase text-[10px] tracking-widest text-center">Items</th>
                                <th class="font-black uppercase text-[10px] tracking-widest text-right">Monto</th>
                                <th class="font-black uppercase text-[10px] tracking-widest">Estado</th>
                            </tr>
                        </thead>
                        <tbody>
                            {#each report.orders as order}
                                <tr class="hover:bg-base-200/50 transition-colors {expandedOrders[order.id] ? 'bg-base-200/30' : ''}">
                                    <td class="print:hidden">
                                        <button 
                                            class="btn btn-ghost btn-xs btn-circle"
                                            onclick={() => toggleOrder(order.id)}
                                        >
                                            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 transition-transform {expandedOrders[order.id] ? 'rotate-180' : ''}" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M19 9l-7 7-7-7" />
                                            </svg>
                                        </button>
                                    </td>
                                    <td class="font-black">#{order.id}</td>
                                    <td class="font-bold opacity-60">{new Date(order.created_at).toLocaleTimeString()}</td>
                                    <td class="font-bold">{order.waiter_name || '—'}</td>
                                    <td>
                                        <div class="badge badge-sm font-black uppercase text-[9px] tracking-tighter">
                                            {order.type === 'TABLE' ? 'Mesa' : 'Llevar'}
                                        </div>
                                    </td>
                                    <td class="text-center font-bold">{order.items_count}</td>
                                    <td class="text-right font-black tabular-nums">{formatCurrency(order.total)}</td>
                                    <td>
                                        <div class="badge badge-sm font-black text-[9px] {order.status === 'PAID' ? 'badge-success' : order.status === 'CANCELLED' ? 'badge-error' : 'badge-ghost'}">
                                            {order.status}
                                        </div>
                                    </td>
                                </tr>
                                
                                {#if expandedOrders[order.id]}
                                    <tr class="bg-base-200/30">
                                        <td colspan="8" class="p-0 border-t-0">
                                            <div class="p-6 space-y-4 animate-in fade-in slide-in-from-top-2 duration-300">
                                                <div class="grid grid-cols-1 gap-3">
                                                    {#each order.items as item}
                                                        <div class="flex items-center justify-between p-3 bg-base-100 rounded-2xl border border-base-content/5 shadow-sm">
                                                            <div class="flex items-center gap-4">
                                                                <div class="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center font-black text-xs">
                                                                    {item.quantity}x
                                                                </div>
                                                                <div>
                                                                    <div class="flex items-center gap-2">
                                                                        <span class="font-black text-sm uppercase">{item.name}</span>
                                                                        {#if item.variant}
                                                                            <span class="badge badge-outline badge-xs font-black uppercase text-[8px] opacity-70">{item.variant}</span>
                                                                        {/if}
                                                                    </div>
                                                                    {#if item.modifiers && item.modifiers.length > 0}
                                                                        <div class="flex flex-wrap gap-1 mt-1">
                                                                            {#each item.modifiers as mod}
                                                                                <span class="text-[9px] font-bold opacity-40 uppercase">· {mod}</span>
                                                                            {/each}
                                                                        </div>
                                                                    {/if}
                                                                </div>
                                                            </div>
                                                            <div class="text-right">
                                                                <span class="font-black text-sm tabular-nums">{formatCurrency(item.price)}</span>
                                                                <div class="text-[9px] opacity-30 font-bold uppercase tracking-widest">Subtotal: {formatCurrency(item.price * item.quantity)}</div>
                                                            </div>
                                                        </div>
                                                    {/each}
                                                </div>
                                            </div>
                                        </td>
                                    </tr>
                                {/if}
                            {/each}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        <!-- Trazabilidad de Seguridad (Logs del Turno) -->
        {#if can.viewReports() && shiftAudits.length > 0}
            <div class="card bg-base-100 border border-error/10 shadow-xl overflow-hidden print:hidden">
                <div class="card-body p-8">
                    <div class="flex items-center justify-between mb-6">
                        <h3 class="font-black uppercase tracking-widest text-xs opacity-50 flex items-center gap-2">
                            <span class="w-1.5 h-4 bg-error rounded-full animate-pulse"></span>
                            Trazabilidad de Seguridad (Logs del Turno)
                        </h3>
                        <span class="badge badge-error badge-sm font-black p-3 text-[10px] tracking-wider uppercase">
                            🛡️ {shiftAudits.length} EVENTOS CRÍTICOS
                        </span>
                    </div>
                    <div class="overflow-x-auto">
                        <table class="table table-md w-full">
                            <thead>
                                <tr class="bg-base-200/50">
                                    <th class="font-bold tracking-widest text-[10px] uppercase opacity-75">Hora</th>
                                    <th class="font-bold tracking-widest text-[10px] uppercase opacity-75">Usuario</th>
                                    <th class="font-bold tracking-widest text-[10px] uppercase opacity-75">Acción</th>
                                    <th class="font-bold tracking-widest text-[10px] uppercase opacity-75">Detalles</th>
                                </tr>
                            </thead>
                            <tbody>
                                {#each shiftAudits as log}
                                    <tr class="hover:bg-base-200/50 transition-colors">
                                        <td class="font-medium opacity-60 whitespace-nowrap text-xs">
                                            {new Date(log.timestamp).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })}
                                        </td>
                                        <td class="font-bold text-xs">{log.actor_name}</td>
                                        <td>
                                            <span class="badge badge-sm font-black uppercase {log.action.includes('DENIED') || log.action.includes('CANCELLED') ? 'badge-error' : 'badge-neutral'} text-[9px]">
                                                {log.action}
                                            </span>
                                        </td>
                                        <td class="text-xs max-w-sm whitespace-normal leading-relaxed">
                                            {#if log.reason}
                                                <span class="italic font-medium opacity-80">"{log.reason}"</span>
                                            {/if}
                                            {#if log.changes_json}
                                                <div class="text-[10px] opacity-40 font-mono mt-1 break-all bg-base-200/60 p-2 rounded-xl border border-base-content/5">
                                                    {log.changes_json}
                                                </div>
                                            {/if}
                                        </td>
                                    </tr>
                                {/each}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        {/if}
    {/if}
</div>

<style>
    @media print {
        :global(body) {
            background: white !important;
            color: black !important;
        }
        :global(.navbar, .footer, .btn, .breadcrumbs) {
            display: none !important;
        }
        .card {
            border: 1px solid #eee !important;
            box-shadow: none !important;
        }
    }
</style>
