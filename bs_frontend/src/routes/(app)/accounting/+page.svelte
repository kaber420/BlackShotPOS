<script lang="ts">
    import { onMount } from 'svelte';
    import { appState, can } from '$lib/app_state.svelte';
    import { checkActiveShift, getShiftReport, listShifts, type ShiftInfo } from '$lib/api/shifts';
    import Button from '$lib/components/ui/Button.svelte';
    import CashMovementModal from '$lib/components/accounting/CashMovementModal.svelte';
    import { toast } from '$lib/toast.svelte';

    let activeShift = $state<ShiftInfo | null>(null);
    let historicalShifts = $state<ShiftInfo[]>([]);
    let isLoading = $state(true);
    let showMovementModal = $state(false);
    let movementType = $state<'INCOME' | 'EXPENSE' | 'WITHDRAWAL'>('EXPENSE');

    async function loadData() {
        isLoading = true;
        try {
            const res = await checkActiveShift();
            activeShift = res.shift;
            historicalShifts = await listShifts();
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
                <div class="mt-4 flex items-center gap-2 text-xs font-bold opacity-60">
                    <span>Fondo: {formatCurrency(activeShift.initial_cash)}</span>
                    <span>•</span>
                    <span>Ventas: {formatCurrency(activeShift.expected_cash - activeShift.initial_cash)}</span>
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
                <div class="text-4xl font-black text-accent tracking-tighter">{formatCurrency(activeShift.expected_cash + activeShift.expected_card + activeShift.expected_transfer - activeShift.initial_cash)}</div>
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
                                        <span class="badge {mov.type === 'INCOME' ? 'badge-success' : 'badge-error'} font-black text-[10px] uppercase">
                                            {mov.type === 'INCOME' ? 'Entrada' : 'Salida'}
                                        </span>
                                    </td>
                                    <td class="text-right font-black {mov.type === 'INCOME' ? 'text-success' : 'text-error'}">
                                        {mov.type === 'INCOME' ? '+' : '-'}{formatCurrency(mov.amount)}
                                    </td>
                                </tr>
                            {/each}
                        {:else}
                            <tr>
                                <td colspan="4" class="text-center py-12 opacity-30 font-bold uppercase tracking-widest">No hay movimientos manuales registrados</td>
                            </tr>
                        {/if}
                    </tbody>
                </table>
            </div>
        </div>
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

    <!-- Historical Shifts -->
    <div class="space-y-6">
        <h2 class="text-2xl font-black tracking-tight">Historial de Turnos</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {#each historicalShifts.filter(s => s.status === 'CLOSED').slice(0, 6) as shift}
                <div class="bg-base-100 p-6 rounded-3xl border border-base-200 hover:border-primary/30 transition-all cursor-pointer group">
                    <div class="flex justify-between items-start mb-4">
                        <div>
                            <div class="font-black text-lg">Corte #{shift.id}</div>
                            <div class="text-xs opacity-50 font-bold">{new Date(shift.start_time).toLocaleDateString()}</div>
                        </div>
                        <div class="badge badge-ghost font-black text-[10px] uppercase">Cerrado</div>
                    </div>
                    <div class="space-y-2">
                        <div class="flex justify-between text-sm">
                            <span class="opacity-50 font-bold">Venta Total:</span>
                            <span class="font-black">{formatCurrency((shift.actual_cash || 0) + (shift.actual_card || 0) + (shift.actual_transfer || 0) - shift.initial_cash)}</span>
                        </div>
                        <div class="flex justify-between text-sm">
                            <span class="opacity-50 font-bold">Diferencia:</span>
                            <span class="font-black {(shift.difference_cash || 0) >= 0 ? 'text-success' : 'text-error'}">
                                {(shift.difference_cash || 0) >= 0 ? '+' : ''}{formatCurrency(shift.difference_cash || 0)}
                            </span>
                        </div>
                    </div>
                    <div class="mt-4 pt-4 border-t border-base-200 group-hover:border-primary/20 flex justify-between items-center">
                        <span class="text-[10px] font-black uppercase tracking-widest opacity-30">Ver detalles</span>
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-primary opacity-0 group-hover:opacity-100 transition-opacity" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" /></svg>
                    </div>
                </div>
            {/each}
        </div>
    </div>
</div>

{#if showMovementModal && activeShift}
    <CashMovementModal 
        shiftId={activeShift.id} 
        initialType={movementType}
        onClose={() => showMovementModal = false} 
        onSuccess={loadData} 
    />
{/if}
