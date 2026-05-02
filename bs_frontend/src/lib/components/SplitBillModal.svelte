<script lang="ts">
    import { appState } from '$lib/app_state.svelte';
    import Button from '$lib/components/ui/Button.svelte';
    import { OrderService, type Order } from '$lib/api/orders';

    let { isOpen, order = null, onClose, onSuccess } = $props<{
        isOpen: boolean;
        order: Order | null;
        onClose: () => void;
        onSuccess: (newOrder: Order) => void;
    }>();

    // Use a flat array of selection objects to ensure deep reactivity in Svelte 5
    let selections = $state<{id: number, qty: number}[]>([]);
    let isLoading = $state(false);

    // Sync selections when modal opens or order changes
    $effect(() => {
        if (isOpen && order) {
            console.log("SplitBillModal: Initializing for order", order.id);
            selections = order.items
                .filter(i => i.status !== 'CANCELLED')
                .map(i => ({ id: i.id, qty: 0 }));
        }
    });

    // Helper to get selection for an item
    function getSelection(id: number) {
        return selections.find(s => s.id === id);
    }

    let totalSplitItems = $derived(selections.reduce((acc, s) => acc + s.qty, 0));

    function selectAll() {
        if (!order) return;
        selections.forEach(s => {
            const item = order.items.find(i => i.id === s.id);
            if (item) s.qty = item.quantity;
        });
    }

    function clearAll() {
        selections.forEach(s => s.qty = 0);
    }

    function increment(itemId: number, maxQty: number) {
        console.log("Incrementing", itemId);
        const sel = getSelection(itemId);
        if (sel && sel.qty < maxQty) {
            sel.qty++;
        }
    }

    function decrement(itemId: number) {
        console.log("Decrementing", itemId);
        const sel = getSelection(itemId);
        if (sel && sel.qty > 0) {
            sel.qty--;
        }
    }

    async function handleSplit() {
        if (!order || totalSplitItems === 0) return;

        const itemsPayload = selections
            .filter(s => s.qty > 0)
            .map(s => ({
                item_id: s.id,
                quantity: s.qty
            }));

        isLoading = true;
        try {
            console.log("Processing split...");
            const newOrder = await OrderService.splitOrder(order.id, itemsPayload);
            onSuccess(newOrder);
        } catch (e) {
            console.error("Split failed", e);
            alert(`Error: ${e}`);
        } finally {
            isLoading = false;
        }
    }
</script>

{#if isOpen && order}
    <!-- Backdrop -->
    <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
    <div 
        class="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-md p-4 animate-in fade-in duration-300"
        onclick={onClose}
    >
        <!-- Modal Content -->
        <div 
            class="bg-base-100 w-full max-w-lg rounded-[2rem] shadow-2xl overflow-hidden flex flex-col max-h-[90vh] border border-base-300 animate-in zoom-in-95 duration-200"
            onclick={(e) => e.stopPropagation()}
        >
            <!-- Header -->
            <div class="bg-secondary p-6 text-white relative">
                <div class="flex justify-between items-start">
                    <div>
                        <h3 class="text-2xl font-black uppercase tracking-tight flex items-center gap-2">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-7 h-7">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M14.25 14.25L19.5 19.5m-15-15l5.25 5.25m-5.25 0V9.75M4.5 4.5h5.25m10.5 5.25v-5.25m0 0h-5.25m-10.5 10.5v5.25m0 0h5.25m10.5-5.25L14.25 14.25" />
                            </svg>
                            Dividir Cuenta
                        </h3>
                        <p class="opacity-70 text-xs font-bold mt-1">Mueve productos a una nueva orden.</p>
                    </div>
                    <button class="w-8 h-8 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors" onclick={onClose}>
                        <span class="font-black">✕</span>
                    </button>
                </div>
            </div>

            <!-- Body -->
            <div class="p-6 flex-1 overflow-hidden flex flex-col gap-4">
                <div class="flex justify-between items-center px-1">
                    <span class="text-[10px] font-black uppercase opacity-40 tracking-widest">Productos</span>
                    <div class="flex gap-4">
                        <button class="text-[10px] font-black uppercase text-primary hover:scale-105 transition-transform" onclick={selectAll}>Seleccionar Todo</button>
                        <button class="text-[10px] font-black uppercase text-error hover:scale-105 transition-transform" onclick={clearAll}>Limpiar</button>
                    </div>
                </div>

                <div class="flex-1 overflow-y-auto elegant-scroll pr-2 flex flex-col gap-3">
                    {#each order.items as item}
                        {#if item.status !== 'CANCELLED'}
                            {@const selection = getSelection(item.id)}
                            <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
                            <div 
                                class="p-4 rounded-2xl border-2 transition-all flex justify-between items-center cursor-pointer select-none
                                    {selection && selection.qty > 0 ? 'bg-primary/5 border-primary shadow-lg shadow-primary/5' : 'bg-base-200 border-transparent hover:border-base-300'}"
                                onclick={() => increment(item.id, item.quantity)}
                            >
                                <div class="flex flex-col gap-1">
                                    <span class="font-black text-sm uppercase tracking-tight {selection && selection.qty > 0 ? 'text-primary' : ''}">
                                        {item.product?.name || 'Producto'}
                                    </span>
                                    <span class="font-mono text-[10px] font-bold opacity-40">${item.unit_price.toFixed(0)} c/u</span>
                                </div>

                                <div class="flex items-center gap-3 bg-base-100 rounded-full p-1 shadow-inner border border-base-300" onclick={(e) => e.stopPropagation()}>
                                    <button 
                                        class="w-8 h-8 rounded-full bg-base-200 hover:bg-base-300 flex items-center justify-center disabled:opacity-20 transition-colors"
                                        onclick={() => decrement(item.id)}
                                        disabled={!selection || selection.qty <= 0}
                                    >
                                        <span class="font-black">-</span>
                                    </button>
                                    <span class="font-mono font-black text-sm w-10 text-center">
                                        {selection?.qty || 0}
                                        <span class="opacity-20 text-[10px]">/{item.quantity}</span>
                                    </span>
                                    <button 
                                        class="w-8 h-8 rounded-full bg-base-200 hover:bg-base-300 flex items-center justify-center disabled:opacity-20 transition-colors"
                                        onclick={() => increment(item.id, item.quantity)}
                                        disabled={!selection || selection.qty >= item.quantity}
                                    >
                                        <span class="font-black">+</span>
                                    </button>
                                </div>
                            </div>
                        {/if}
                    {/each}
                </div>
            </div>

            <!-- Footer -->
            <div class="p-6 bg-base-200 border-t border-base-300 flex flex-col gap-3">
                <Button 
                    variant="primary" 
                    size="lg" 
                    class="w-full bg-secondary hover:bg-secondary/90 text-white font-black uppercase tracking-widest py-6 rounded-2xl shadow-xl shadow-secondary/20"
                    disabled={totalSplitItems === 0 || isLoading}
                    {isLoading}
                    onclick={handleSplit}
                >
                    Separar {totalSplitItems} Ítems
                </Button>
                <button class="text-[10px] font-black uppercase opacity-40 hover:opacity-100 transition-opacity" onclick={onClose}>
                    Cerrar sin cambios
                </button>
            </div>
        </div>
    </div>
{/if}

<style>
    .elegant-scroll::-webkit-scrollbar { width: 4px; }
    .elegant-scroll::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.1); border-radius: 10px; }
</style>
