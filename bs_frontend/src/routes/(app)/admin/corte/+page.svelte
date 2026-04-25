<script lang="ts">
    import { onMount } from 'svelte';
    import { checkActiveShift, closeShift, getShiftReport } from '$lib/api/shifts';
    import Button from '$lib/components/ui/Button.svelte';
    
    let isChecking = $state(true);
    let shiftReport = $state<any>(null);
    let isClosing = $state(false);
    let actualCash = $state(0);
    let closedShiftData = $state<any>(null);

    onMount(async () => {
        await loadShiftData();
    });

    async function loadShiftData() {
        try {
            isChecking = true;
            const res = await checkActiveShift();
            setActiveShift(res.shift);

            if (res.shift) {
                shiftReport = await getShiftReport(res.shift.id);
            }
        } catch (e) {
            console.error(e);
        } finally {
            isChecking = false;
        }
    }

    async function handleCloseShift() {
        if (!appState.activeShift) return;
        
        isClosing = true;
        try {
            const result = await closeShift(appState.activeShift.id, actualCash);
            closedShiftData = await getShiftReport(result.id);
            setActiveShift(null);
        } catch (e) {
            alert("Error cerrando turno: " + e);
        } finally {
            isClosing = false;
        }
    }
</script>

<div class="p-6 max-w-4xl mx-auto">
    <div class="flex items-center gap-4 mb-8">
        <div class="w-12 h-12 rounded-2xl bg-primary/20 flex items-center justify-center text-primary">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
        </div>
        <div>
            <h1 class="text-3xl font-black">Corte de Caja</h1>
            <p class="text-base-content/60 font-medium">Arqueo y cierre del turno actual</p>
        </div>
    </div>

    {#if isChecking}
        <div class="flex justify-center p-12">
            <span class="loading loading-spinner loading-lg text-primary"></span>
        </div>
    {:else if closedShiftData}
        <!-- TICKET DE CIERRE -->
        <div class="card bg-base-100 shadow-xl border border-base-200">
            <div class="card-body items-center text-center">
                <h2 class="card-title text-2xl text-success font-black mb-2">¡Turno Cerrado Exitosamente!</h2>
                <div class="w-full max-w-md bg-base-200 p-6 rounded-xl font-mono text-sm text-left">
                    <p class="text-center font-bold text-lg mb-4 border-b border-base-300 pb-2">REPORTE Z - BLACKSHOT</p>
                    <div class="flex justify-between mb-1"><span>ID Turno:</span> <span>#{closedShiftData.shift_id}</span></div>
                    <div class="flex justify-between mb-1"><span>Estado:</span> <span>{closedShiftData.status}</span></div>
                    <br>
                    <div class="flex justify-between mb-1"><span>Fondo Inicial:</span> <span>${closedShiftData.initial_cash.toFixed(2)}</span></div>
                    <div class="flex justify-between mb-1"><span>Ventas Efectivo:</span> <span>${closedShiftData.sales.cash.toFixed(2)}</span></div>
                    <div class="flex justify-between mb-1 text-primary font-bold border-t border-base-300 pt-1 mt-1"><span>TOTAL ESPERADO:</span> <span>${closedShiftData.expected_cash.toFixed(2)}</span></div>
                    <br>
                    <div class="flex justify-between mb-1"><span>Físico Contado:</span> <span>${closedShiftData.actual_cash.toFixed(2)}</span></div>
                    
                    <div class="flex justify-between mt-2 pt-2 border-t border-base-300 font-bold {closedShiftData.difference < 0 ? 'text-error' : (closedShiftData.difference > 0 ? 'text-warning' : 'text-success')}">
                        <span>{closedShiftData.difference < 0 ? 'Faltante:' : (closedShiftData.difference > 0 ? 'Sobrante:' : 'Diferencia:')}</span> 
                        <span>${Math.abs(closedShiftData.difference).toFixed(2)}</span>
                    </div>

                    <br>
                    <div class="flex justify-between mb-1"><span>Ventas Tarjeta:</span> <span>${closedShiftData.sales.card.toFixed(2)}</span></div>
                    <div class="flex justify-between mb-1"><span>Transferencias:</span> <span>${closedShiftData.sales.transfer.toFixed(2)}</span></div>
                    <div class="flex justify-between mb-1 font-bold"><span>TOTAL VENTAS:</span> <span>${closedShiftData.sales.total.toFixed(2)}</span></div>
                </div>
                <div class="card-actions mt-6">
                    <Button variant="outline" onclick={() => window.print()}>Imprimir Reporte</Button>
                    <Button variant="primary" onclick={() => window.location.href = '/'}>Volver al Dashboard</Button>
                </div>
            </div>
        </div>
    {:else if appState.activeShift && shiftReport}
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <!-- Resumen Informativo -->
            <div class="card bg-base-100 shadow-xl border border-base-200">
                <div class="card-body">
                    <h2 class="card-title text-xl font-bold mb-4">Métricas del Turno</h2>
                    
                    <div class="stats stats-vertical bg-base-200 shadow-sm border border-base-300">
                        <div class="stat">
                            <div class="stat-title font-bold">Fondo Inicial</div>
                            <div class="stat-value text-primary">${shiftReport.initial_cash.toFixed(2)}</div>
                        </div>
                        
                        <div class="stat">
                            <div class="stat-title font-bold">Cobrado en Efectivo</div>
                            <div class="stat-value">${shiftReport.sales.cash.toFixed(2)}</div>
                            <div class="stat-desc">Generado por ventas</div>
                        </div>
                        
                        <div class="stat bg-primary/10">
                            <div class="stat-title font-bold text-primary">Caja Esperada</div>
                            <div class="stat-value text-primary">${shiftReport.expected_cash.toFixed(2)}</div>
                            <div class="stat-desc font-bold">Fondo Inicial + Ventas Efectivo</div>
                        </div>
                    </div>

                    <div class="mt-4 p-4 bg-base-200 rounded-xl">
                        <h3 class="font-bold mb-2">Otros Métodos (No cuentan para caja)</h3>
                        <div class="flex justify-between text-sm mb-1"><span>Tarjeta:</span> <span class="font-bold">${shiftReport.sales.card.toFixed(2)}</span></div>
                        <div class="flex justify-between text-sm"><span>Transferencia:</span> <span class="font-bold">${shiftReport.sales.transfer.toFixed(2)}</span></div>
                    </div>
                </div>
            </div>

            <!-- Formulario de Arqueo -->
            <div class="card bg-base-100 shadow-xl border border-primary/20">
                <div class="card-body">
                    <h2 class="card-title text-xl font-bold text-primary mb-4">Arqueo de Caja</h2>
                    <p class="text-sm opacity-70 mb-4">Cuenta el dinero físico que hay en el cajón y escríbelo aquí. El sistema comparará esto contra la "Caja Esperada".</p>
                    
                    <div class="form-control w-full my-auto">
                        <label class="label">
                            <span class="label-text font-black text-lg">Efectivo Físico Contado</span>
                        </label>
                        <div class="join w-full shadow-md">
                            <span class="join-item btn btn-active pointer-events-none font-black text-2xl bg-base-200 border-base-300 text-base-content/50">$</span>
                            <input type="number" step="0.01" min="0" bind:value={actualCash} placeholder="0.00" class="input input-bordered input-lg join-item w-full text-3xl font-black text-right text-primary focus:border-primary" />
                        </div>
                        
                        {#if actualCash > 0}
                            <div class="mt-4 p-4 rounded-xl border font-bold flex justify-between
                                {(actualCash - shiftReport.expected_cash) === 0 ? 'bg-success/10 border-success text-success' : 
                                ((actualCash - shiftReport.expected_cash) > 0 ? 'bg-warning/10 border-warning text-warning' : 'bg-error/10 border-error text-error')}">
                                <span>Diferencia calculada:</span>
                                <span>
                                    {(actualCash - shiftReport.expected_cash) > 0 ? '+' : ''}
                                    ${(actualCash - shiftReport.expected_cash).toFixed(2)}
                                </span>
                            </div>
                        {/if}
                    </div>

                    <div class="card-actions mt-auto pt-6">
                        <Button 
                            variant="primary" 
                            size="lg" 
                            class="btn-block font-black" 
                            onclick={handleCloseShift} 
                            disabled={actualCash === 0}
                            isLoading={isClosing}
                        >
                            Cerrar Caja y Generar Reporte
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    {:else}
        <div class="alert alert-warning shadow-lg">
            <div>
                <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current flex-shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                <span class="font-bold">No hay un turno activo en este momento. La caja ya está cerrada.</span>
            </div>
        </div>
    {/if}
</div>
