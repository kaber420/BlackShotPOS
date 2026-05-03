<script lang="ts">
    import { addCashMovement } from '$lib/api/shifts';
    import Button from '$lib/components/ui/Button.svelte';
    import { toast } from '$lib/toast.svelte';

    interface Props {
        shiftId: number;
        onClose?: () => void;
        onSuccess?: () => void;
    }

    let { shiftId, onClose, onSuccess }: Props = $props();

    let amount = $state(0);
    let type = $state<'INCOME' | 'EXPENSE'>('EXPENSE');
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
            toast.success("Movimiento registrado");
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
    <div class="modal-box shadow-2xl border border-base-content/10">
        <h3 class="font-black text-2xl mb-6 flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-8 h-8 {type === 'INCOME' ? 'text-success' : 'text-error'}">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v12m-3-3l3 3 3-3m-3-9V6m0 0l3 3m-3-3l-3 3" />
            </svg>
            Nuevo Movimiento de Caja
        </h3>

        <div class="space-y-4">
            <div class="flex p-1 bg-base-200 rounded-xl">
                <button 
                    class="flex-1 py-2 rounded-lg font-black text-sm transition-all {type === 'EXPENSE' ? 'bg-error text-error-content shadow-lg' : 'opacity-50'}"
                    onclick={() => type = 'EXPENSE'}
                >
                    SALIDA (GASTO)
                </button>
                <button 
                    class="flex-1 py-2 rounded-lg font-black text-sm transition-all {type === 'INCOME' ? 'bg-success text-success-content shadow-lg' : 'opacity-50'}"
                    onclick={() => type = 'INCOME'}
                >
                    ENTRADA (INGRESO)
                </button>
            </div>

            <div class="form-control">
                <label class="label"><span class="label-text font-bold">Monto</span></label>
                <div class="join w-full">
                    <span class="join-item btn btn-active pointer-events-none">$</span>
                    <input type="number" step="0.01" bind:value={amount} class="input input-bordered join-item w-full font-black text-xl" placeholder="0.00" />
                </div>
            </div>

            <div class="form-control">
                <label class="label"><span class="label-text font-bold">Concepto / Motivo</span></label>
                <input type="text" bind:value={reason} class="input input-bordered w-full font-medium" placeholder="Ej: Pago de hielo, Fondo extra..." />
            </div>
        </div>

        <div class="modal-action mt-8 flex gap-3">
            <Button variant="ghost" onclick={onClose}>Cancelar</Button>
            <Button 
                variant={type === 'INCOME' ? 'success' : 'danger'} 
                class="flex-1 font-black" 
                onclick={handleSubmit}
                isLoading={isSubmitting}
            >
                Registrar Movimiento
            </Button>
        </div>
    </div>
</div>
