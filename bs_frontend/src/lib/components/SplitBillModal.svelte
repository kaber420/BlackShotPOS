<script lang="ts">
    import { appState } from '$lib/app_state.svelte';
    import Button from '$lib/components/ui/Button.svelte';
    import { OrderService, type Order } from '$lib/api/orders';

    let { isOpen, order = null, onClose, onSuccess } = $props<{
        isOpen: boolean;
        order: Order | null;
        onClose: () => void;
        onSuccess: () => void;
    }>();

    let splitItems = $state<Record<number, number>>({});
    let isLoading = $state(false);

    // Reset state when opened or order changes
    $effect(() => {
        if (isOpen && order) {
            splitItems = {};
            // Inicializar con 0
            order.items.forEach(item => {
                if (item.status !== 'CANCELLED') {
                    splitItems[item.id] = 0;
                }
            });
        }
    });

    let totalSplitItems = $derived(Object.values(splitItems).reduce((a, b) => a + b, 0));

    function increment(itemId: number, maxQty: number) {
        if (splitItems[itemId] < maxQty) {
            splitItems[itemId]++;
        }
    }

    function decrement(itemId: number) {
        if (splitItems[itemId] > 0) {
            splitItems[itemId]--;
        }
    }

    async function handleSplit() {
        if (!order || totalSplitItems === 0) return;

        const itemsPayload = Object.entries(splitItems)
            .filter(([_, qty]) => qty > 0)
            .map(([id, qty]) => ({
                item_id: Number(id),
                quantity: qty
            }));

        isLoading = true;
        try {
            await OrderService.splitOrder(order.id, itemsPayload);
            onSuccess();
        } catch (e) {
            alert(`Error al dividir cuenta: ${e}`);
        } finally {
            isLoading = false;
        }
    }
</script>

{#if isOpen && order}
<div class="modal modal-open bg-base-300/60 backdrop-blur-sm z-[70]">
    <div class="modal-box max-w-lg p-0 overflow-hidden shadow-2xl border border-base-200">
        <!-- Header -->
        <div class="bg-secondary text-secondary-content p-6">
            <h3 class="text-2xl font-black uppercase tracking-widest flex items-center gap-2">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-8 h-8">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M14.25 14.25L19.5 19.5m-15-15l5.25 5.25m-5.25 0V9.75M4.5 4.5h5.25m10.5 5.25v-5.25m0 0h-5.25m-10.5 10.5v5.25m0 0h5.25m10.5-5.25L14.25 14.25" />
                </svg>
                Dividir Cuenta
            </h3>
            <p class="opacity-80 font-bold mt-1">Selecciona los productos para mover a una nueva orden.</p>
        </div>

        <div class="p-6 flex flex-col gap-4">
            <div class="max-h-[50vh] overflow-y-auto pr-2 elegant-scroll flex flex-col gap-3">
                {#each order.items as item}
                    {#if item.status !== 'CANCELLED'}
                        <div class="flex justify-between items-center bg-base-200/50 p-4 rounded-[1rem] border border-base-200">
                            <div class="flex flex-col">
                                <span class="font-black text-sm uppercase tracking-tight">{item.product?.name || 'Producto'}</span>
                                <span class="font-mono text-primary text-xs font-bold">${item.unit_price.toFixed(2)} c/u</span>
                            </div>
                            
                            <!-- Counter -->
                            <div class="flex items-center bg-base-100 rounded-full p-1 border border-base-300 shadow-sm gap-2">
                                <button 
                                    class="w-8 h-8 flex items-center justify-center rounded-full bg-base-200 hover:bg-base-300 transition-colors disabled:opacity-30"
                                    onclick={() => decrement(item.id)}
                                    disabled={splitItems[item.id] === 0}
                                >
                                    <span class="font-black">-</span>
                                </button>
                                <span class="font-black text-sm w-6 text-center">{splitItems[item.id] || 0} / {item.quantity}</span>
                                <button 
                                    class="w-8 h-8 flex items-center justify-center rounded-full bg-base-200 hover:bg-base-300 transition-colors disabled:opacity-30"
                                    onclick={() => increment(item.id, item.quantity)}
                                    disabled={splitItems[item.id] === item.quantity}
                                >
                                    <span class="font-black">+</span>
                                </button>
                            </div>
                        </div>
                    {/if}
                {/each}
            </div>

            <div class="flex flex-col gap-3 mt-4">
                <Button 
                    variant="primary" 
                    size="lg" 
                    class="shadow-xl bg-secondary hover:bg-secondary/90 border-none text-white font-black uppercase tracking-widest" 
                    disabled={totalSplitItems === 0} 
                    {isLoading}
                    onclick={handleSplit}
                >
                    Separar {totalSplitItems} Ítems
                </Button>
                <Button variant="ghost" size="sm" class="opacity-60" onclick={onClose}>Cancelar</Button>
            </div>
        </div>
    </div>
</div>
{/if}

<style>
    .elegant-scroll::-webkit-scrollbar { width: 4px; }
    .elegant-scroll::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.1); border-radius: 10px; }
</style>
