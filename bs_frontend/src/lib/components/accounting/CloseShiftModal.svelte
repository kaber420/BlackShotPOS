<script lang="ts">
    import { closeShift, type ShiftInfo } from '$lib/api/shifts';
    import { appState, setActiveShift } from '$lib/app_state.svelte';
    import Button from '$lib/components/ui/Button.svelte';
    import CashCounter from './CashCounter.svelte';
    import { toast } from '$lib/toast.svelte';

    interface Props {
        shift: ShiftInfo;
        onClose?: () => void;
    }

    let { shift, onClose }: Props = $props();

    let step = $state(1); // 1: Cash, 2: Others, 3: Summary
    let actualCash = $state(0);
    let actualCard = $state(0);
    let actualTransfer = $state(0);
    let notes = $state('');
    let isClosing = $state(false);

    let diffCash = $derived(actualCash - (shift.expected_cash || 0));
    let diffCard = $derived(actualCard - (shift.expected_card || 0));
    let diffTransfer = $derived(actualTransfer - (shift.expected_transfer || 0));

    async function handleClose() {
        isClosing = true;
        try {
            const closedShift = await closeShift(shift.id, {
                actual_cash: actualCash,
                actual_card: actualCard,
                actual_transfer: actualTransfer,
                notes
            });
            setActiveShift(null);
            toast.success("Turno cerrado correctamente");
            onClose?.();
        } catch (e: any) {
            toast.error("Error al cerrar turno: " + (e.detail || e.message));
        } finally {
            isClosing = false;
        }
    }
</script>

<div class="modal modal-open bg-base-300/80 backdrop-blur-sm z-50">
    <div class="modal-box max-w-2xl shadow-2xl border border-base-content/10">
        <div class="flex items-center justify-between mb-6">
            <div class="flex items-center gap-4">
                <div class="w-12 h-12 bg-secondary/10 rounded-xl flex items-center justify-center text-secondary">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-8 h-8">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M9 14.25l1.25 1.25L13.75 12m2.25 2.25l1.25-1.25L21 18.75m-18 0l1.25-1.25L6 15m12 0l1.25 1.25L21 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5m-18 0h18" />
                    </svg>
                </div>
                <div>
                    <h3 class="font-black text-2xl tracking-tighter">Cierre de Caja (Corte Z)</h3>
                    <p class="text-xs opacity-50 font-bold uppercase tracking-widest">Turno #{shift.id}</p>
                </div>
            </div>
            <button class="btn btn-ghost btn-sm btn-circle" onclick={onClose}>✕</button>
        </div>

        <!-- Progress Steps -->
        <ul class="steps w-full mb-8">
            <li class="step {step >= 1 ? 'step-primary' : ''} font-bold text-xs">EFECTIVO</li>
            <li class="step {step >= 2 ? 'step-primary' : ''} font-bold text-xs">VOUCHERS</li>
            <li class="step {step >= 3 ? 'step-primary' : ''} font-bold text-xs">RESUMEN</li>
        </ul>

        {#if step === 1}
            <div class="space-y-4">
                <CashCounter onTotalChange={(t) => actualCash = t} />
                <div class="form-control">
                    <label class="label"><span class="label-text font-bold">Total Efectivo Contado</span></label>
                    <input type="number" bind:value={actualCash} class="input input-bordered input-lg font-black text-2xl text-right" />
                </div>
                <Button variant="primary" class="btn-block" onclick={() => step = 2}>Siguiente: Vouchers</Button>
            </div>
        {:else if step === 2}
            <div class="space-y-6">
                <div class="form-control">
                    <label class="label"><span class="label-text font-black text-xs uppercase tracking-widest opacity-50">Total Tarjetas (Vouchers)</span></label>
                    <input type="number" bind:value={actualCard} class="input input-bordered input-lg font-black text-2xl text-right text-secondary" />
                </div>
                <div class="form-control">
                    <label class="label"><span class="label-text font-black text-xs uppercase tracking-widest opacity-50">Total Transferencias</span></label>
                    <input type="number" bind:value={actualTransfer} class="input input-bordered input-lg font-black text-2xl text-right text-accent" />
                </div>
                <div class="flex gap-3">
                    <Button variant="ghost" class="flex-1" onclick={() => step = 1}>Atrás</Button>
                    <Button variant="primary" class="flex-2" onclick={() => step = 3}>Ver Resumen</Button>
                </div>
            </div>
        {:else if step === 3}
            <div class="space-y-6">
                <div class="bg-base-200 p-6 rounded-2xl border border-base-300 space-y-4">
                    <div class="flex justify-between items-center pb-2 border-b border-base-300">
                        <span class="font-bold opacity-60">Efectivo</span>
                        <div class="text-right">
                            <div class="font-black">${actualCash.toFixed(2)}</div>
                            <div class="text-xs font-bold {diffCash >= 0 ? 'text-success' : 'text-error'}">
                                {diffCash >= 0 ? '+' : ''}{diffCash.toFixed(2)} diff
                            </div>
                        </div>
                    </div>
                    <div class="flex justify-between items-center pb-2 border-b border-base-300">
                        <span class="font-bold opacity-60">Tarjetas</span>
                        <div class="text-right">
                            <div class="font-black">${actualCard.toFixed(2)}</div>
                            <div class="text-xs font-bold {diffCard >= 0 ? 'text-success' : 'text-error'}">
                                {diffCard >= 0 ? '+' : ''}{diffCard.toFixed(2)} diff
                            </div>
                        </div>
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="font-bold opacity-60">Transferencias</span>
                        <div class="text-right">
                            <div class="font-black">${actualTransfer.toFixed(2)}</div>
                            <div class="text-xs font-bold {diffTransfer >= 0 ? 'text-success' : 'text-error'}">
                                {diffTransfer >= 0 ? '+' : ''}{diffTransfer.toFixed(2)} diff
                            </div>
                        </div>
                    </div>
                </div>

                <div class="form-control">
                    <label class="label"><span class="label-text font-bold">Notas de Cierre</span></label>
                    <textarea bind:value={notes} class="textarea textarea-bordered h-20" placeholder="Observaciones sobre faltantes, sobrantes o incidencias..."></textarea>
                </div>

                <div class="flex gap-3">
                    <Button variant="ghost" class="flex-1" onclick={() => step = 2}>Atrás</Button>
                    <Button 
                        variant="danger" 
                        class="flex-2 font-black h-14" 
                        onclick={handleClose}
                        isLoading={isClosing}
                    >
                        CONFIRMAR Y CERRAR CAJA
                    </Button>
                </div>
            </div>
        {/if}
    </div>
</div>
