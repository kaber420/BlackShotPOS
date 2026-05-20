<script lang="ts">
    import { onMount } from 'svelte';
    import { appState, can } from '$lib/app_state.svelte';
    import { checkActiveShift, getShiftReport, type ShiftInfo } from '$lib/api/shifts';
    import Button from '$lib/components/ui/Button.svelte';
    import CashMovementModal from '$lib/components/accounting/CashMovementModal.svelte';
    import { toast } from '$lib/toast.svelte';
    import { goto } from '$app/navigation';
    import { formatDateTime } from '$lib/utils';

    let activeShift = $state<ShiftInfo | null>(null);
    let isLoading = $state(true);
    let showMovementModal = $state(false);
    let movementType = $state<'INCOME' | 'EXPENSE' | 'WITHDRAWAL'>('EXPENSE');
    let activeShiftReport = $state<any>(null);
    let expandedOrders = $state<Record<number, boolean>>({});

    function toggleOrder(id: number) {
        expandedOrders[id] = !expandedOrders[id];
    }

    async function loadData() {
        isLoading = true;
        try {
            const res = await checkActiveShift();
            activeShift = res.shift;
            if (activeShift) {
                activeShiftReport = await getShiftReport(activeShift.id);
            }
        } catch (e) {
            console.error("Error loading accounting data", e);
        } finally {
            isLoading = false;
        }
    }

    function openMovement(type: 'INCOME' | 'EXPENSE' | 'WITHDRAWAL') {
        movementType = type;
        showMovementModal = true;
    }

    onMount(loadData);

    function formatCurrency(amount: number) {
        return new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(amount);
    }
</script>

<div class="p-4 lg:p-8 space-y-8 max-w-7xl mx-auto pb-24">
    <!-- Header -->
    <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div>
            <h1 class="text-4xl font-black tracking-tighter text-base-content">Control de <span class="text-primary">Caja</span></h1>
            {#if activeShift}
                <div class="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2">
                    <div class="flex items-center gap-1.5 text-xs font-black uppercase tracking-wider bg-base-200 px-2.5 py-1 rounded-lg">
                        <span class="opacity-40">Turno:</span> 
                        <span class="text-primary">#{activeShift.id}</span>
                    </div>
                    <div class="flex items-center gap-1.5 text-xs font-black uppercase tracking-wider bg-base-200 px-2.5 py-1 rounded-lg">
                        <span class="opacity-40">Cajero:</span> 
                        <span>{appState.userName || 'N/A'}</span>
                    </div>
                </div>
            {:else}
                <p class="text-base-content/60 font-medium uppercase tracking-widest text-xs mt-1">Gestión de turnos y arqueos financieros</p>
            {/if}
        </div>
        
        {#if activeShift}
            <div class="flex flex-wrap gap-2">
                <Button variant="danger" outline class="font-black text-[10px] uppercase tracking-widest px-6" onclick={() => openMovement('EXPENSE')}>
                    💸 Registrar Gasto
                </Button>
                <Button variant="info" outline class="font-black text-[10px] uppercase tracking-widest px-6" onclick={() => openMovement('WITHDRAWAL')}>
                    🛡️ Retiro de Seguridad
                </Button>
                <div class="w-px h-10 bg-base-300 mx-2 hidden md:block"></div>
                {#if activeShiftReport && activeShiftReport.orders.length > 0}
                    <Button variant="ghost" class="font-black text-[10px] uppercase tracking-widest px-6 gap-2" onclick={() => document.getElementById('order-register')?.scrollIntoView({ behavior: 'smooth' })}>
                        📋 Registro ({activeShiftReport.orders.length})
                    </Button>
                {/if}
                <Button variant="primary" class="font-black text-[10px] uppercase tracking-widest px-8 shadow-lg shadow-primary/20" onclick={() => setShowCloseShiftModal(true)}>
                    🏁 Cerrar Turno (Corte Z)
                </Button>
            </div>
        {/if}
    </div>

    {#if isLoading}
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="h-32 bg-base-100 animate-pulse rounded-3xl"></div>
            <div class="h-32 bg-base-100 animate-pulse rounded-3xl"></div>
            <div class="h-32 bg-base-100 animate-pulse rounded-3xl"></div>
        </div>
    {:else if activeShift}
        <!-- Active Shift Summary (Corte X) -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <!-- Cash Card -->
            <div class="bg-base-100 p-6 rounded-3xl border border-base-200 shadow-sm relative overflow-hidden group">
                <div class="absolute top-0 right-0 p-4 opacity-5 group-hover:scale-110 transition-transform duration-500">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-24 w-24" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" /></svg>
                </div>
                <h3 class="text-xs font-black opacity-40 uppercase tracking-widest mb-1">Efectivo en Caja</h3>
                <div class="text-4xl font-black text-primary tracking-tighter">{formatCurrency(activeShift.expected_cash)}</div>
                <div class="mt-4 flex flex-wrap items-center gap-2 text-xs font-bold opacity-60">
                    <span>Fondo: {formatCurrency(activeShift.initial_cash)}</span>
                    <span>•</span>
                    <span>Ventas: {formatCurrency(activeShiftReport?.sales?.cash ?? 0)}</span>
                    {#if (activeShift.expenses ?? 0) > 0}
                        <span>•</span>
                        <span class="text-error">Gastos: -{formatCurrency(activeShift.expenses ?? 0)}</span>
                    {/if}
                    {#if (activeShift.withdrawals ?? 0) > 0}
                        <span>•</span>
                        <span class="text-info">Retiros: -{formatCurrency(activeShift.withdrawals ?? 0)}</span>
                    {/if}
                </div>
            </div>

            <!-- Card Card -->
            <div class="bg-base-100 p-6 rounded-3xl border border-base-200 shadow-sm relative overflow-hidden group">
                <div class="absolute top-0 right-0 p-4 opacity-5 group-hover:scale-110 transition-transform duration-500">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-24 w-24" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" /></svg>
                </div>
                <h3 class="text-xs font-black opacity-40 uppercase tracking-widest mb-1">Tarjetas / Vouchers</h3>
                <div class="text-4xl font-black text-secondary tracking-tighter">{formatCurrency(activeShift.expected_card)}</div>
                <div class="mt-4 text-xs font-bold opacity-60 uppercase tracking-widest">Registrado por ventas</div>
            </div>

            <!-- Total Card -->
            <div class="bg-base-100 p-6 rounded-3xl border border-base-200 shadow-sm relative overflow-hidden group">
                <div class="absolute top-0 right-0 p-4 opacity-5 group-hover:scale-110 transition-transform duration-500">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-24 w-24" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
                </div>
                <h3 class="text-xs font-black opacity-40 uppercase tracking-widest mb-1">Venta Total Bruta</h3>
                <div class="text-4xl font-black text-accent tracking-tighter">{formatCurrency(activeShiftReport?.sales?.total ?? 0)}</div>
                <div class="mt-4 text-xs font-bold opacity-60 uppercase tracking-widest">Sin incluir fondo inicial</div>
            </div>
        </div>

        <!-- Movements Table -->
        <div class="bg-base-100 rounded-3xl border border-base-200 shadow-sm overflow-hidden">
            <div class="p-6 border-b border-base-200 flex justify-between items-center">
                <h3 class="font-black text-xl tracking-tight">Movimientos de Efectivo</h3>
                <div class="badge badge-primary font-bold px-4 py-3">TURNO ACTUAL</div>
            </div>
            <div class="overflow-x-auto">
                <table class="table table-lg">
                    <thead class="bg-base-200/50">
                        <tr class="text-xs font-black uppercase tracking-widest">
                            <th>Hora</th>
                            <th>Concepto</th>
                            <th>Categoría</th>
                            <th>Registrado por</th>
                            <th>Tipo</th>
                            <th class="text-right">Monto</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#if activeShift.movements && activeShift.movements.length > 0}
                            {#each activeShift.movements as mov}
                                <tr class="hover:bg-base-200/30 transition-colors">
                                    <td class="font-bold opacity-50">{new Date(mov.timestamp).toLocaleTimeString()}</td>
                                    <td class="font-black">{mov.reason}</td>
                                    <td>
                                        {#if mov.category_name}
                                            <span class="badge badge-ghost font-bold text-[10px] uppercase">{mov.category_name}</span>
                                        {:else}
                                            <span class="opacity-20 text-xs">—</span>
                                        {/if}
                                    </td>
                                    <td class="font-bold opacity-60 text-sm">
                                        {mov.actor_name || '—'}
                                    </td>
                                    <td>
                                        <span class="badge {mov.type === 'INCOME' ? 'badge-success' : mov.type === 'WITHDRAWAL' ? 'badge-info' : 'badge-error'} font-black text-[10px] uppercase">
                                            {mov.type === 'INCOME' ? 'Entrada' : mov.type === 'WITHDRAWAL' ? 'Retiro' : 'Salida'}
                                        </span>
                                    </td>
                                    <td class="text-right font-black {mov.type === 'INCOME' ? 'text-success' : 'text-error'}">
                                        {mov.type === 'INCOME' ? '+' : '-'}{formatCurrency(mov.amount)}
                                    </td>
                                </tr>
                            {/each}
                        {:else}
                            <tr>
                                <td colspan="6" class="text-center py-12 opacity-30 font-bold uppercase tracking-widest">No hay movimientos manuales registrados</td>
                            </tr>
                        {/if}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Registro de Órdenes (Table requested by user) -->
        {#if activeShiftReport && activeShiftReport.orders.length > 0}
            <div id="order-register" class="bg-base-100 rounded-3xl border border-base-200 shadow-sm overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-700">
                <div class="p-6 border-b border-base-200 flex justify-between items-center bg-base-200/20">
                    <div class="flex items-center gap-3">
                        <div class="w-1.5 h-6 bg-primary rounded-full"></div>
                        <h3 class="font-black text-xl tracking-tight uppercase">Registro de Órdenes <span class="opacity-30">({activeShiftReport.orders.length})</span></h3>
                    </div>
                    <Button variant="ghost" size="sm" class="font-black text-[10px] uppercase" onclick={() => goto(`/admin/shifts/${activeShift.id}`)}>
                        Ver Auditoría Completa ↗
                    </Button>
                </div>
                <div class="overflow-x-auto">
                    <table class="table table-md">
                        <thead class="bg-base-200/50">
                            <tr class="text-[10px] font-black uppercase tracking-widest opacity-60">
                                <th class="w-10"></th>
                                <th>Ticket</th>
                                <th>Hora</th>
                                <th>Mesero</th>
                                <th>Tipo</th>
                                <th class="text-center">Items</th>
                                <th class="text-right">Monto</th>
                                <th>Estado</th>
                            </tr>
                        </thead>
                        <tbody>
                            {#each activeShiftReport.orders as order}
                                <tr class="hover:bg-base-200/50 transition-colors {expandedOrders[order.id] ? 'bg-base-200/30' : ''}">
                                    <td>
                                        <button 
                                            class="btn btn-ghost btn-xs btn-circle"
                                            onclick={() => toggleOrder(order.id)}
                                        >
                                            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 transition-transform {expandedOrders[order.id] ? 'rotate-180' : ''}" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M19 9l-7 7-7-7" />
                                            </svg>
                                        </button>
                                    </td>
                                    <td class="font-black text-primary">#{order.id}</td>
                                    <td class="font-bold opacity-60 tabular-nums">{new Date(order.created_at).toLocaleTimeString()}</td>
                                    <td class="font-bold">{order.waiter_name || '—'}</td>
                                    <td>
                                        <div class="badge badge-outline font-black uppercase text-[9px] tracking-tighter">
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
                                            <div class="p-6 space-y-3 animate-in fade-in slide-in-from-top-2 duration-300">
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
                                        </td>
                                    </tr>
                                {/if}
                            {/each}
                        </tbody>
                    </table>
                </div>
            </div>
        {/if}
    {:else}
        <!-- No Active Shift State -->
        <div class="bg-base-100 rounded-3xl border-2 border-dashed border-base-300 p-20 text-center space-y-4">
            <div class="w-24 h-24 bg-base-200 rounded-full flex items-center justify-center mx-auto text-base-content/20">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-12 h-12">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
            </div>
            <h2 class="text-2xl font-black tracking-tight">No hay un turno de caja abierto</h2>
            <p class="text-base-content/50 max-w-md mx-auto font-medium">Debes abrir un turno desde el inicio o el botón de abajo para poder registrar ventas y movimientos.</p>
            <Button variant="primary" size="lg" class="font-black px-12" onclick={() => window.location.href = '/'}>Ir al Inicio y Abrir Caja</Button>
        </div>
    {/if}


</div>

{#if showMovementModal && activeShift}
    <CashMovementModal 
        shiftId={activeShift.id} 
        initialType={movementType}
        onClose={() => showMovementModal = false} 
        onSuccess={loadData} 
    />
{/if}
