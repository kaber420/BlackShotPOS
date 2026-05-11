<script lang="ts">
    import { appState } from '$lib/app_state.svelte';
    import Button from '$lib/components/ui/Button.svelte';
    import { TableService } from '$lib/api/tables';
    import { OrderService, OrderStatus, type Order } from '$lib/api/orders';
    import { loadOrderToCart, setActiveTable } from '$lib/app_state.svelte';
    import SplitBillModal from './SplitBillModal.svelte';
    import { goto } from '$app/navigation';

    let { 
        isOpen = false, 
        table = null, 
        order = null, 
        onClose = () => {}, 
        onAddMore = () => {}, 
        onCheckout = () => {}, 
        onActionComplete = () => {} 
    } = $props();

    let isProcessing = $state(false);

    // Calculation logic for totals with tax
    let subtotal = $derived(order?.subtotal ?? 0);
    let taxAmount = $derived(order?.tax_amount ?? 0);
    let totalWithTax = $derived(order?.total_amount ?? 0);
    let balanceDue = $derived(order?.balance_due ?? totalWithTax);
    let paidAmount = $derived(totalWithTax - balanceDue);
    
    let isSplitBillOpen = $state(false);

    // Split calculator state
    let numPeople = $state(1);
    let amountPerPerson = $derived(balanceDue / (numPeople || 1));

    $effect(() => {
        if (isOpen && balanceDue > 0) {
            appState.suggestedPaymentAmount = amountPerPerson;
            appState.suggestedPeopleCount = numPeople;
        }
    });

    function handleSplitSuccess(newOrder: Order) {
        isSplitBillOpen = false;
        
        // Cargar la nueva orden directamente al carrito para cobro inmediato
        loadOrderToCart(newOrder);
        appState.activeTable = table;
        appState.cartVisible = true;
        
        onActionComplete();
        onClose(); 
    }

    async function handleVacate() {
        if (!table) return;
        
        const hasActiveOrder = order && order.items && order.items.length > 0;
        const msg = hasActiveOrder 
            ? `⚠️ ATENCIÓN: La mesa ${table.number} tiene productos sin cobrar. Liberarla manualmente puede causar descuadres. ¿Realmente deseas CONTINUAR?`
            : `¿Estás seguro de que deseas liberar la mesa ${table.number}?`;
            
        if (!confirm(msg)) return;
        
        isProcessing = true;
        try {
            await TableService.vacate(table.id);
            onActionComplete();
            onClose();
        } catch (e) {
            alert(`Error: ${e}`);
        } finally {
            isProcessing = false;
        }
    }

    function getOrderTotal(items: any[]) {
        if (!items) return 0;
        return items.reduce((acc, item) => acc + (item.unit_price * item.quantity), 0);
    }

    async function handleCancelOrDelete() {
        if (!order) return;
        const hasItems = order.items && order.items.length > 0;
        const msg = hasItems 
            ? "⚠️ ¿Estás seguro de que deseas ANULAR este pedido? Se mantendrá el registro de cancelación para auditoría."
            : "¿Deseas eliminar este pedido vacío?";
        if (!confirm(msg)) return;
        isProcessing = true;
        try {
            if (hasItems) await OrderService.updateStatus(order.id, OrderStatus.CANCELLED);
            else await OrderService.delete(order.id);
            onActionComplete();
            onClose();
        } catch (e) {
            alert(`Error: ${e}`);
        } finally {
            isProcessing = false;
        }
    }
</script>

{#if isOpen && table}
    <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
    <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md p-4 animate-in fade-in duration-300" onclick={onClose}>
        <div class="bg-base-100 w-full max-w-lg rounded-[2.5rem] shadow-[0_32px_64px_-12px_rgba(0,0,0,0.3)] overflow-hidden flex flex-col max-h-[90vh] border border-base-200 animate-in zoom-in-95 duration-200" onclick={(e) => e.stopPropagation()}>
            
            <!-- Header -->
            <div class="bg-primary p-8 text-primary-content relative overflow-hidden">
                <div class="absolute -top-10 -right-10 w-40 h-40 bg-white/10 rounded-full blur-3xl"></div>
                <div class="flex justify-between items-start relative z-10">
                    <div>
                        <div class="flex items-center gap-3">
                            <h2 class="text-4xl font-black tracking-tighter">Mesa {table.number}</h2>
                            <span class="badge badge-outline text-white/70 font-black text-[10px] tracking-widest border-white/20 px-3">OCUPADA</span>
                        </div>
                    </div>
                    <button class="w-10 h-10 bg-white/10 hover:bg-white/20 rounded-full flex items-center justify-center transition-all active:scale-90" onclick={onClose}>
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="3" stroke="currentColor" class="w-4 h-4"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                    </button>
                </div>
            </div>

            <!-- Body -->
            <div class="p-8 overflow-y-auto flex-1 bg-base-200/20 elegant-scroll">
                {#if order}
                    <div class="flex items-center justify-between mb-4 px-1">
                        <h3 class="font-black text-[10px] uppercase tracking-widest opacity-40">Consumo de la Mesa</h3>
                        <span class="text-[10px] font-bold opacity-30 uppercase tracking-tighter">ORDEN #{order.id}</span>
                    </div>
                    
                    {#if order.items && order.items.length > 0}
                        <div class="flex flex-col gap-3">
                            {#each order.items as item}
                                <div class="flex justify-between items-center bg-base-100 p-4 rounded-[1.2rem] border border-base-200 shadow-sm transition-all hover:shadow-md">
                                    <div class="flex flex-col">
                                        <div class="flex items-center gap-2">
                                            <span class="w-6 h-6 rounded-lg bg-base-200 flex items-center justify-center text-[10px] font-black">{item.quantity}</span>
                                            <span class="font-black text-xs uppercase tracking-tight">{item.product?.name || 'Producto'}</span>
                                        </div>
                                        {#if item.modifiers?.length > 0}
                                            <div class="flex flex-wrap gap-1 mt-2 ml-8">
                                                {#each item.modifiers as mod}
                                                    <span class="text-[8px] font-bold uppercase opacity-40 bg-base-200 px-1.5 py-0.5 rounded-md">+ {mod.name}</span>
                                                {/each}
                                            </div>
                                        {/if}
                                    </div>
                                    <span class="font-mono font-black text-sm text-primary tracking-tighter">${(item.unit_price * item.quantity).toFixed(0)}</span>
                                </div>
                            {/each}
                        </div>
                    {:else}
                        <div class="text-center py-12 bg-base-100 rounded-3xl border border-dashed border-base-300 opacity-40">
                            <p class="font-bold text-sm uppercase tracking-widest">Sin productos aún</p>
                        </div>
                    {/if}
                {:else}
                    <div class="flex flex-col items-center justify-center py-16 text-center gap-6 bg-base-100 rounded-3xl border border-dashed border-base-300 mx-1">
                        <div class="w-20 h-20 bg-warning/10 text-warning rounded-full flex items-center justify-center">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                        </div>
                        <p class="text-xl font-black uppercase tracking-tight">Ocupada sin Pedido</p>
                    </div>
                {/if}
            </div>

            <!-- Footer -->
            <div class="p-8 bg-base-100 border-t border-base-200 flex flex-col gap-6">
                <div class="flex justify-between items-end px-1">
                    <div>
                        <span class="text-[10px] font-black opacity-30 uppercase tracking-[0.2em] block mb-1">Saldo Pendiente</span>
                        <span class="text-5xl font-black text-primary font-mono tracking-tighter">${balanceDue.toFixed(2)}</span>
                        <div class="flex flex-col gap-1 mt-2 opacity-60 text-[10px] font-black uppercase tracking-widest">
                            <span class="text-success">Pagado: ${paidAmount.toFixed(2)}</span>
                            <span>Total Original: ${totalWithTax.toFixed(2)}</span>
                        </div>
                    </div>

                    {#if balanceDue > 0}
                        <div class="bg-base-200/50 p-4 rounded-2xl border border-base-200 flex flex-col items-center gap-2">
                            <span class="text-[9px] font-black opacity-40 uppercase tracking-widest">Calculadora de División</span>
                            <div class="flex items-center gap-3">
                                <button 
                                    class="w-8 h-8 rounded-full bg-base-100 hover:bg-base-200 flex items-center justify-center font-black transition-colors"
                                    onclick={() => numPeople = Math.max(1, numPeople - 1)}
                                >-</button>
                                <div class="flex flex-col items-center">
                                    <span class="text-lg font-black">{numPeople}</span>
                                    <span class="text-[8px] font-bold uppercase opacity-40">Personas</span>
                                </div>
                                <button 
                                    class="w-8 h-8 rounded-full bg-base-100 hover:bg-base-200 flex items-center justify-center font-black transition-colors"
                                    onclick={() => numPeople++}
                                >+</button>
                            </div>
                            <div class="divider my-0 opacity-20"></div>
                            <div class="flex flex-col items-center">
                                <span class="text-[9px] font-bold uppercase opacity-40">Cada quien paga</span>
                                <span class="text-xl font-black text-secondary">${amountPerPerson.toFixed(2)}</span>
                            </div>
                            <div class="flex gap-2 mt-1">
                                <button class="text-[8px] font-black bg-base-100 hover:bg-primary/20 px-2 py-1 rounded-md border border-base-300 transition-colors" onclick={() => { numPeople = 2; }}>50%</button>
                                <button class="text-[8px] font-black bg-base-100 hover:bg-primary/20 px-2 py-1 rounded-md border border-base-300 transition-colors" onclick={() => { numPeople = 3; }}>33%</button>
                                <button class="text-[8px] font-black bg-base-100 hover:bg-primary/20 px-2 py-1 rounded-md border border-base-300 transition-colors" onclick={() => { numPeople = 4; }}>25%</button>
                            </div>
                        </div>
                    {/if}
                </div>
                
                <div class="grid grid-cols-3 gap-3">
                    <button 
                        class="flex-1 bg-base-200 hover:bg-base-300 text-base-content rounded-2xl py-5 font-black uppercase tracking-widest text-[10px] transition-all active:scale-95" 
                        onclick={() => order ? onAddMore() : (setActiveTable(table, null), goto('/'))}
                    >
                        Añadir Productos
                    </button>

                    <button 
                        class="flex-1 bg-secondary text-white rounded-2xl py-5 font-black uppercase tracking-widest text-[10px] transition-all active:scale-95 shadow-xl shadow-secondary/20 disabled:opacity-50" 
                        onclick={() => isSplitBillOpen = true}
                        disabled={isProcessing || !order?.items?.length}
                    >
                        Dividir Cuenta
                    </button>
                    
                    <button 
                        class="flex-1 bg-primary text-white rounded-2xl py-5 font-black uppercase tracking-widest text-[10px] transition-all active:scale-95 shadow-xl shadow-primary/20 disabled:opacity-50" 
                        onclick={onCheckout}
                        disabled={isProcessing || !order?.items?.length || balanceDue <= 0}
                    >
                        {balanceDue <= 0 ? 'Pagado' : 'Cobrar'}
                    </button>
                </div>

                <div class="mt-2 p-4 bg-error/5 rounded-3xl border border-error/10 flex flex-col items-center gap-3">
                    <p class="text-[9px] font-bold text-error/50 uppercase tracking-[0.2em] text-center">Zona Crítica de Control</p>
                    <div class="flex gap-2 w-full">
                        {#if order}
                            <button 
                                class="flex-1 text-[9px] font-black text-error/60 hover:text-error hover:bg-error/10 py-3 rounded-xl transition-all uppercase tracking-widest border border-error/10" 
                                onclick={handleCancelOrDelete}
                                disabled={isProcessing}
                            >
                                {order.items?.length ? "Anular Pedido" : "Borrar Orden"}
                            </button>
                        {/if}
                        <button 
                            class="flex-1 text-[9px] font-black text-error/60 hover:text-error hover:bg-error/10 py-3 rounded-xl transition-all uppercase tracking-widest border border-error/10" 
                            onclick={handleVacate}
                            disabled={isProcessing}
                        >
                            Liberar Mesa
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
{/if}

<SplitBillModal 
    isOpen={isSplitBillOpen}
    order={order}
    onClose={() => isSplitBillOpen = false}
    onSuccess={handleSplitSuccess}
/>

<style>
    .elegant-scroll::-webkit-scrollbar {
        width: 4px;
    }
    .elegant-scroll::-webkit-scrollbar-thumb {
        background: rgba(0,0,0,0.1);
        border-radius: 10px;
    }
</style>
