<script lang="ts">
    import { addCashMovement } from '$lib/api/shifts';
    import Button from '$lib/components/ui/Button.svelte';
    import { toast } from '$lib/toast.svelte';

    interface Props {
        shiftId: number;
        onClose?: () => void;
        onSuccess?: () => void;
        initialType?: 'INCOME' | 'EXPENSE' | 'WITHDRAWAL';
    }

    let { shiftId, onClose, onSuccess, initialType = 'EXPENSE' }: Props = $props();

    let amount = $state(0);
    let type = $state<'INCOME' | 'EXPENSE' | 'WITHDRAWAL'>(initialType);
    let reason = $state('');
    let isSubmitting = $state(false);

    async function handleSubmit() {
        if (amount <= 0 || !reason) {
            toast.error("Ingresa un monto y motivo válido");
            return;
        }
        isSubmitting = true;
        try {
            await addCashMovement(shiftId, { amount, type, reason });
            toast.success(type === 'WITHDRAWAL' ? "Retiro registrado" : "Movimiento registrado");
            onSuccess?.();
            onClose?.();
        } catch (e: any) {
            toast.error("Error: " + (e.detail || e.message));
        } finally {
            isSubmitting = false;
        }
    }
</script>

<div class="modal modal-open bg-base-300/80 backdrop-blur-sm z-50">
    <div class="modal-box shadow-2xl border border-base-content/10 max-w-lg">
        <h3 class="font-black text-2xl mb-6 flex items-center gap-2">
            <div class="w-10 h-10 rounded-xl flex items-center justify-center {type === 'INCOME' ? 'bg-success/20 text-success' : type === 'WITHDRAWAL' ? 'bg-info/20 text-info' : 'bg-error/20 text-error'}">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-6 h-6">
                    {#if type === 'INCOME'}
                        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m0 0l6.75-6.75M12 19.5l-6.75-6.75" />
                    {:else}
                        <path stroke-linecap="round" stroke-linejoin="round" d="M12 19.5v-15m0 0l-6.75 6.75M12 4.5l6.75 6.75" />
                    {/if}
                </svg>
            </div>
            {type === 'WITHDRAWAL' ? 'Retiro de Seguridad' : 'Nuevo Movimiento de Caja'}
        </h3>

        <div class="space-y-6">
            <div class="flex p-1 bg-base-200 rounded-2xl gap-1">
                <button 
                    class="flex-1 py-3 rounded-xl font-black text-[10px] uppercase tracking-widest transition-all {type === 'EXPENSE' ? 'bg-error text-white shadow-lg' : 'opacity-50 hover:bg-base-300'}"
                    onclick={() => type = 'EXPENSE'}
                >
                    Gasto
                </button>
                <button 
                    class="flex-1 py-3 rounded-xl font-black text-[10px] uppercase tracking-widest transition-all {type === 'WITHDRAWAL' ? 'bg-info text-white shadow-lg' : 'opacity-50 hover:bg-base-300'}"
                    onclick={() => type = 'WITHDRAWAL'}
                >
                    Retiro Seg.
                </button>
                <button 
                    class="flex-1 py-3 rounded-xl font-black text-[10px] uppercase tracking-widest transition-all {type === 'INCOME' ? 'bg-success text-white shadow-lg' : 'opacity-50 hover:bg-base-300'}"
                    onclick={() => type = 'INCOME'}
                >
                    Ingreso
                </button>
            </div>

            <div class="space-y-4">
                <div class="form-control">
                    <label class="label"><span class="label-text font-black text-xs uppercase tracking-widest opacity-60">Monto del {type === 'INCOME' ? 'Ingreso' : type === 'WITHDRAWAL' ? 'Retiro' : 'Gasto'}</span></label>
                    <div class="relative">
                        <span class="absolute left-4 top-1/2 -translate-y-1/2 font-black text-2xl opacity-20">$</span>
                        <input 
                            type="number" 
                            step="0.01" 
                            bind:value={amount} 
                            class="input input-bordered w-full h-16 pl-10 font-black text-3xl text-right bg-base-200/50" 
                            placeholder="0.00" 
                            autofocus
                        />
                    </div>
                </div>

                <div class="form-control">
                    <label class="label"><span class="label-text font-black text-xs uppercase tracking-widest opacity-60">Concepto / Motivo</span></label>
                    <input 
                        type="text" 
                        bind:value={reason} 
                        class="input input-bordered w-full font-bold h-12 bg-base-200/30" 
                        placeholder={type === 'WITHDRAWAL' ? 'Ej: Corte Parcial #1' : type === 'EXPENSE' ? 'Ej: Pago de Hielo' : 'Ej: Fondo extra'} 
                    />
                </div>
            </div>
        </div>

        <div class="modal-action mt-10 grid grid-cols-2 gap-3">
            <Button variant="ghost" size="lg" class="font-black uppercase tracking-widest text-[11px]" onclick={onClose}>Cancelar</Button>
            <Button 
                variant={type === 'INCOME' ? 'success' : type === 'WITHDRAWAL' ? 'info' : 'danger'} 
                size="lg"
                class="font-black uppercase tracking-widest text-[11px]" 
                onclick={handleSubmit}
                isLoading={isSubmitting}
            >
                Confirmar {type === 'INCOME' ? 'Ingreso' : type === 'WITHDRAWAL' ? 'Retiro' : 'Gasto'}
            </Button>
        </div>
    </div>
</div>
