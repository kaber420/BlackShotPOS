<script lang="ts">
    import { page } from '$app/state';
    import { fetchApi } from '$lib/api';
    import { onMount } from 'svelte';
    import { formatCurrency, formatDateTime } from '$lib/utils';
    import Button from '$lib/components/ui/Button.svelte';
    import { goto } from '$app/navigation';

    let report: any = $state(null);
    let loading = $state(true);
    const shiftId = $derived(Number(page.params.id));

    onMount(async () => {
        try {
            report = await fetchApi(`/api/v1/pos/shifts/${shiftId}/report`);
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
                Auditoría de <span class="text-primary">Turno #{shiftId}</span>
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
                        Resumen del Turno
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
                                    {report.shift.difference === 0 ? '平衡 Balanceado' : report.shift.difference > 0 ? '📈 Sobrante' : '📉 Faltante'}
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
        <div class="card bg-base-100 border border-base-content/5 shadow-2xl overflow-hidden print:shadow-none print:border-none">
            <div class="card-body p-8">
                <div class="flex items-center justify-between mb-6">
                    <h3 class="font-black uppercase tracking-widest text-xs opacity-50">Registro de Órdenes ({report.orders.length})</h3>
                </div>
                <div class="overflow-x-auto">
                    <table class="table table-md">
                        <thead>
                            <tr class="bg-base-200/50">
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
                                <tr class="hover:bg-base-200/50 transition-colors">
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
                            {/each}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
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
