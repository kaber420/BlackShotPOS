<script lang="ts">
    import { onMount } from 'svelte';
    import { getRegisters, openShift, type CashRegister } from '$lib/api/shifts';
    import { appState, setActiveShift } from '$lib/app_state.svelte';
    import Button from '$lib/components/ui/Button.svelte';
    import CashCounter from './CashCounter.svelte';

    let registers = $state<CashRegister[]>([]);
    let selectedRegisterId = $state<number | null>(null);
    let initialCash = $state(0);
    let isLoadingRegisters = $state(true);
    let isOpening = $state(false);
    let showCalculator = $state(false);

    onMount(async () => {
        try {
            registers = await getRegisters();
            if (registers.length > 0) {
                selectedRegisterId = registers[0].id;
            }
        } catch (e) {
            console.error("Error loading registers", e);
        } finally {
            isLoadingRegisters = false;
        }
    });

    async function handleOpen() {
        // En este modelo, el register_id es opcional (Caja por Usuario)
        isOpening = true;
        try {
            const shift = await openShift(initialCash, selectedRegisterId);
            setActiveShift(shift);
        } catch (e: any) {
            alert("Error al abrir turno: " + (e.detail || e.message || e));
        } finally {
            isOpening = false;
        }
    }
</script>

<div class="modal modal-open bg-base-300/80 backdrop-blur-sm z-50">
    <div class="modal-box max-w-2xl shadow-2xl border border-base-content/10">
        <div class="flex items-center gap-4 mb-6">
            <div class="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center text-primary">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-10 h-10">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
            </div>
            <div>
                <h3 class="font-black text-3xl text-base-content tracking-tighter">Apertura de Caja</h3>
                <p class="text-base-content/60 font-medium">Inicia un nuevo turno para comenzar a vender.</p>
            </div>
        </div>

        <div class="space-y-6">
            <!-- Selección de Caja -->
            <div class="form-control w-full">
                <label class="label">
                    <span class="label-text font-black uppercase tracking-widest text-xs opacity-50">1. Seleccionar Punto de Venta</span>
                </label>
                {#if isLoadingRegisters}
                    <div class="h-12 bg-base-200 animate-pulse rounded-xl"></div>
                {:else}
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {#each registers as reg}
                            <button 
                                class="btn btn-outline h-auto py-4 flex-col gap-1 items-start rounded-2xl border-2 transition-all duration-200 {selectedRegisterId === reg.id ? 'btn-primary bg-primary/5' : 'border-base-300'}"
                                onclick={() => selectedRegisterId = reg.id}
                            >
                                <span class="font-black text-lg">{reg.name}</span>
                                <span class="text-xs opacity-60">ID: #{reg.id}</span>
                            </button>
                        {/each}
                        {#if registers.length === 0}
                            <div class="col-span-full p-6 bg-base-200/50 rounded-2xl border-2 border-dashed border-base-300 flex flex-col items-center justify-center text-center">
                                <span class="text-xs font-black uppercase tracking-widest opacity-40 mb-1">Caja por Usuario</span>
                                <p class="text-xs font-medium opacity-60">No hay cajas físicas registradas. Tu turno será personal.</p>
                            </div>
                        {/if}
                    </div>
                {/if}
            </div>

            <!-- Fondo Inicial -->
            <div class="form-control w-full">
                <div class="flex justify-between items-end mb-2">
                    <label class="label p-0">
                        <span class="label-text font-black uppercase tracking-widest text-xs opacity-50">2. Fondo Inicial (Efectivo)</span>
                    </label>
                    <button 
                        class="btn btn-ghost btn-xs text-primary font-bold"
                        onclick={() => showCalculator = !showCalculator}
                    >
                        {showCalculator ? 'Ocultar Calculadora' : 'Usar Calculadora'}
                    </button>
                </div>

                {#if showCalculator}
                    <div class="mb-4">
                        <CashCounter onTotalChange={(t) => initialCash = t} />
                    </div>
                {/if}

                <div class="join w-full shadow-sm">
                    <span class="join-item btn btn-active pointer-events-none font-black text-xl bg-base-200 border-base-300 text-base-content/30">$</span>
                    <input 
                        type="number" 
                        step="0.01" 
                        min="0" 
                        bind:value={initialCash} 
                        placeholder="0.00" 
                        class="input input-bordered input-lg join-item w-full text-2xl font-black text-right focus:border-primary" 
                    />
                </div>
            </div>
        </div>

        <div class="modal-action mt-10">
            <Button 
                variant="primary" 
                size="lg" 
                class="btn-block h-16 text-xl font-black rounded-2xl shadow-xl shadow-primary/20" 
                onclick={handleOpen} 
                disabled={initialCash < 0}
                isLoading={isOpening}
            >
                Abrir Turno Ahora
            </Button>
        </div>
    </div>
</div>
