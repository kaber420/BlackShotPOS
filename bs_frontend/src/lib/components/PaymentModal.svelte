<script lang="ts">
    import { appState } from '$lib/app_state.svelte';
    import Button from '$lib/components/ui/Button.svelte';

    let { isOpen, total, onConfirm, onClose, hasTable = true } = $props();

    let paymentMethod = $state<string>('CASH');
    let amountReceived = $state<number>(0);
    let shouldPrint = $state<boolean>(true);
    let vacateTable = $state<boolean>(true);
    let isLoading = $state(false);

    let change = $derived(Math.max(0, amountReceived - total));
    let isAmountSufficient = $derived(paymentMethod !== 'CASH' || amountReceived >= total);

    function selectMethod(method: string) {
        paymentMethod = method;
        if (method !== 'CASH') {
            amountReceived = total;
        }
    }

    function addCash(amount: number) {
        if (amount === 0) {
            amountReceived = 0;
        } else {
            amountReceived += amount;
        }
    }

    function setExact() {
        amountReceived = total;
    }

    async function handleProcess() {
        if (!isAmountSufficient) return;
        
        isLoading = true;
        try {
            await onConfirm(paymentMethod, amountReceived, shouldPrint, vacateTable);
        } finally {
            isLoading = false;
        }
    }
</script>

{#if isOpen}
<div class="modal modal-open bg-base-300/60 backdrop-blur-sm z-[60]">
    <div class="modal-box max-w-2xl p-0 overflow-hidden shadow-2xl border border-base-200">
        <!-- Header -->
        <div class="bg-primary text-primary-content p-6">
            <h3 class="text-2xl font-black uppercase tracking-widest flex items-center gap-2">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-8 h-8">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 18.75a60.07 60.07 0 0115.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75m0 1.5v.75m0 1.5v.75m0 1.5V15h1.5V4.5H3.75zm15 0v.75m0 1.5v.75m0 1.5v.75m0 1.5V15h1.5V4.5h-1.5zm-15 0a2.25 2.25 0 00-2.25 2.25v10.5c0 1.242 1.008 2.25 2.25 2.25h15a2.25 2.25 0 002.25-2.25V6.75A2.25 2.25 0 0018.75 4.5H3.75zM6.75 11.25a.75.75 0 100-1.5.75.75 0 000 1.5zm0 3a.75.75 0 100-1.5.75.75 0 000 1.5zm3-3a.75.75 0 100-1.5.75.75 0 000 1.5zm0 3a.75.75 0 100-1.5.75.75 0 000 1.5zm3-3a.75.75 0 100-1.5.75.75 0 000 1.5zm0 3a.75.75 0 100-1.5.75.75 0 000 1.5zm3-3a.75.75 0 100-1.5.75.75 0 000 1.5zm0 3a.75.75 0 100-1.5.75.75 0 000 1.5z" />
                </svg>
                Finalizar Venta
            </h3>
            <p class="opacity-80 font-bold mt-1">Selecciona método de pago y registra el ingreso.</p>
        </div>

        <div class="p-6 grid grid-cols-1 md:grid-cols-2 gap-8">
            <!-- Left Side: Methods & Inputs -->
            <div class="flex flex-col gap-6">
                <div>
                    <span class="text-[10px] font-black uppercase tracking-widest opacity-60 mb-3 block">Método de Pago</span>
                    <div class="grid grid-cols-3 gap-2">
                        <Button 
                            variant={paymentMethod === 'CASH' ? 'primary' : 'outline'}
                            class="h-20 flex flex-col gap-1 items-center justify-center {paymentMethod === 'CASH' ? 'shadow-inner' : ''}" 
                            onclick={() => selectMethod('CASH')}
                        >
                            <span class="text-xl">💵</span>
                            <span class="text-[10px] font-black">EFECTIVO</span>
                        </Button>
                        <Button 
                            variant={paymentMethod === 'CARD' ? 'primary' : 'outline'}
                            class="h-20 flex flex-col gap-1 items-center justify-center {paymentMethod === 'CARD' ? 'shadow-inner' : ''}" 
                            onclick={() => selectMethod('CARD')}
                        >
                            <span class="text-xl">💳</span>
                            <span class="text-[10px] font-black">TARJETA</span>
                        </Button>
                        <Button 
                            variant={paymentMethod === 'TRANSFER' ? 'primary' : 'outline'}
                            class="h-20 flex flex-col gap-1 items-center justify-center {paymentMethod === 'TRANSFER' ? 'shadow-inner' : ''}" 
                            onclick={() => selectMethod('TRANSFER')}
                        >
                            <span class="text-xl">📲</span>
                            <span class="text-[10px] font-black">TRANSF.</span>
                        </Button>
                    </div>
                </div>

                {#if paymentMethod === 'CASH'}
                <div class="animate-in fade-in slide-in-from-top-4 duration-300">
                    <label class="label p-0 mb-2" for="cash_input">
                        <span class="label-text font-black uppercase text-[10px] tracking-widest opacity-60">Efectivo Recibido</span>
                    </label>
                    <div class="join w-full shadow-sm">
                        <span class="join-item btn btn-active pointer-events-none font-black text-lg bg-base-200">{appState.settings.currency_symbol}</span>
                        <input 
                            id="cash_input"
                            type="number" 
                            step="0.01" 
                            bind:value={amountReceived} 
                            class="input input-bordered join-item w-full text-2xl font-black text-right focus:border-primary" 
                            placeholder="0.00"
                        />
                    </div>
                    
                    <div class="grid grid-cols-4 gap-2 mt-3">
                        <Button size="sm" class="font-bold" onclick={() => addCash(20)}>+20</Button>
                        <Button size="sm" class="font-bold" onclick={() => addCash(50)}>+50</Button>
                        <Button size="sm" class="font-bold" onclick={() => addCash(100)}>+100</Button>
                        <Button size="sm" class="font-bold" onclick={() => addCash(200)}>+200</Button>
                        <Button size="sm" class="font-bold" onclick={() => addCash(500)}>+500</Button>
                        <Button variant="outline" size="sm" class="font-bold col-span-2" onclick={setExact}>Exacto</Button>
                        <Button variant="ghost" size="sm" danger class="font-bold" onclick={() => addCash(0)}>Cero</Button>
                    </div>
                </div>
                {/if}

                <div class="flex items-center justify-between p-4 bg-base-200 rounded-xl border border-base-300">
                    <div class="flex items-center gap-3">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-6 h-6 opacity-60">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M6.72 13.829c-.24.03-.48.062-.72.096m.72-.096a42.415 42.415 0 0110.56 0m-10.56 0L6.34 18m10.94-4.171c.24.03.48.062.72.096m-.72-.096L17.66 18m0 0l.229 2.523a1.125 1.125 0 01-1.12 1.227H7.231a1.125 1.125 0 01-1.12-1.227L6.34 18m11.318-3.071A3 3 0 0014.122 12H9.878a3 3 0 00-2.878 2.378L6.34 18m11.318-3.071c1.118-.119 2.232-.26 3.342-.424a.75.75 0 00.612-.732V6.378a.75.75 0 00-.612-.732 42.42 42.42 0 00-3.342-.424M6.34 18a42.42 42.42 0 01-3.342-.424.75.75 0 01-.612-.732V6.378a.75.75 0 01.612-.732 42.423 42.423 0 013.342-.424M15 9h.008v.008H15V9zm0 3h.008v.008H15V12zm0-6h.008v.008H15V6zm-3 6h.008v.008H12V12zm0-3h.008v.008H12V9zm0-6h.008v.008H12V6zM9 9h.008v.008H9V9zm0 3h.008v.008H9V12zm0-6h.008v.008H9V6z" />
                        </svg>
                        <span class="font-bold text-sm">Ticket</span>
                    </div>
                    <input type="checkbox" class="toggle toggle-primary toggle-sm" bind:checked={shouldPrint} />
                </div>

                {#if hasTable}
                <div class="flex items-center justify-between p-4 bg-base-200 rounded-xl border border-base-300">
                    <div class="flex items-center gap-3">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-6 h-6 opacity-60">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9" />
                        </svg>
                        <span class="font-bold text-sm">Liberar Mesa</span>
                    </div>
                    <input type="checkbox" class="toggle toggle-secondary toggle-sm" bind:checked={vacateTable} />
                </div>
                {/if}
            </div>

            <!-- Right Side: Totals & Summary -->
            <div class="bg-base-200/50 rounded-2xl p-6 border border-base-200 flex flex-col justify-between">
                <div>
                   <h4 class="text-[10px] font-black uppercase tracking-widest opacity-60 mb-4">Resumen de Cuenta</h4>
                   
                   <div class="flex flex-col gap-2">
                        <div class="flex justify-between items-center text-sm opacity-70">
                            <span>Monto Total</span>
                            <span>{appState.settings.currency_symbol}{total.toFixed(2)}</span>
                        </div>
                        <div class="flex justify-between items-center text-sm opacity-70">
                            <span>Recibido</span>
                            <span>{appState.settings.currency_symbol}{amountReceived.toFixed(2)}</span>
                        </div>
                        
                        <div class="divider my-1"></div>
                        
                        <div class="flex flex-col items-center py-4">
                            <span class="text-[10px] font-black uppercase tracking-tighter opacity-50 mb-1">Tu Cambio (Feria)</span>
                            <span class="text-5xl font-black text-primary font-serif">
                                {appState.settings.currency_symbol}{change.toFixed(2)}
                            </span>
                        </div>
                   </div>
                </div>

                <div class="flex flex-col gap-3 mt-8">
                    <Button 
                        variant="primary" 
                        size="lg" 
                        class="shadow-xl shadow-primary/20 text-white font-black uppercase tracking-widest" 
                        disabled={!isAmountSufficient} 
                        {isLoading}
                        onclick={handleProcess}
                    >
                        Confirmar Cobro
                    </Button>
                    <Button variant="ghost" size="sm" class="opacity-60" onclick={onClose}>Cancelar</Button>
                </div>
            </div>
        </div>
    </div>
</div>
{/if}
