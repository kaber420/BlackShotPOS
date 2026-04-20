<script lang="ts">
    import { appState } from '$lib/app_state.svelte';
    import Button from '$lib/components/ui/Button.svelte';
    import { TableService } from '$lib/api/tables';
    import { OrderService, OrderStatus } from '$lib/api/orders';

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

    async function handleVacate() {
        if (!table) return;
        if (!confirm(`¿Estás seguro de que deseas desocupar la mesa ${table.number} manualmente?`)) return;
        
        isProcessing = true;
        try {
            const result = await TableService.vacate(table.id);
            alert(`Mesa desocupada. Tiempo de ocupación: ${result.duration_minutes} minutos.`);
            onActionComplete();
            onClose();
        } catch (e) {
            alert(`Error: ${e}`);
        } finally {
            isProcessing = false;
        }
    }

    // Helper to calculate total safely
    function getOrderTotal(items: any[]) {
        if (!items) return 0;
        return items.reduce((acc, item) => {
            const itemTotal = item.unit_price * item.quantity;
            return acc + itemTotal;
        }, 0);
    }

    async function handleCancelOrDelete() {
        if (!order) return;
        
        const hasItems = order.items && order.items.length > 0;
        const msg = hasItems 
            ? "¿Estás seguro de que deseas CANCELAR este pedido? (La mesa se liberará pero el registro queda para auditoría)"
            : "¿Estás seguro de que deseas ELIMINAR este pedido vacío?";
            
        if (!confirm(msg)) return;
        
        isProcessing = true;
        try {
            if (hasItems) {
                await OrderService.updateStatus(order.id, OrderStatus.CANCELLED);
            } else {
                await OrderService.delete(order.id);
            }
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
    <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200" onclick={onClose}>
        <div class="bg-base-100 w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]" onclick={(e) => e.stopPropagation()}>
            <!-- Header -->
            <div class="bg-primary text-primary-content p-6">
                <div class="flex justify-between items-start">
                    <div>
                        <h2 class="text-3xl font-black">Mesa {table.number}</h2>
                        <p class="text-xs font-bold uppercase tracking-widest opacity-80 mt-1">Resumen de Cuenta</p>
                    </div>
                    <Button variant="ghost" circle size="sm" class="text-primary-content" onclick={onClose}>✕</Button>
                </div>
            </div>

            <!-- Body -->
            <div class="p-6 overflow-y-auto flex-1 bg-base-200/30">
                {#if order}
                    <h3 class="font-bold text-sm uppercase tracking-wide opacity-60 mb-4 border-b border-base-300 pb-2">Pedidos Actuales</h3>
                    
                    {#if order.items && order.items.length > 0}
                        <div class="flex flex-col gap-3">
                            {#each order.items as item}
                                <div class="flex justify-between items-start bg-base-100 p-3 rounded-xl border border-base-200 shadow-sm">
                                    <div class="flex flex-col">
                                        <span class="font-bold text-sm">{item.quantity}x {item.product?.name || 'Producto'}</span>
                                        {#if item.modifiers && item.modifiers.length > 0}
                                            <div class="flex flex-col mt-1">
                                                {#each item.modifiers as mod}
                                                    <span class="text-[10px] opacity-60 leading-none">+ {mod.name}</span>
                                                {/each}
                                            </div>
                                        {/if}
                                    </div>
                                    <span class="font-bold text-sm text-primary">${(item.unit_price * item.quantity).toFixed(2)}</span>
                                </div>
                            {/each}
                        </div>
                    {:else}
                        <div class="text-center py-8 opacity-50">
                            <p>No hay productos en esta orden.</p>
                        </div>
                    {/if}
                {:else}
                    <div class="flex flex-col items-center justify-center py-12 text-center gap-4">
                        <div class="w-16 h-16 bg-error/10 text-error rounded-full flex items-center justify-center">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </div>
                        <div>
                            <p class="text-lg font-bold">Mesa Ocupada sin Orden</p>
                            <p class="text-sm opacity-60">La mesa está marcada como ocupada pero no tiene pedidos activos en este momento.</p>
                        </div>
                    </div>
                {/if}
            </div>

            <!-- Totals & Actions -->
            <div class="p-6 bg-base-100 border-t border-base-200">
                <div class="flex justify-between items-end mb-6">
                    <span class="text-sm font-bold opacity-60 uppercase">Total Estimado</span>
                    <span class="text-3xl font-black text-primary font-serif">${order ? getOrderTotal(order.items).toFixed(2) : '0.00'}</span>
                </div>
                
                <div class="grid grid-cols-2 gap-3">
                    <Button variant="outline" class="gap-2" onclick={() => {
                        if (!order) {
                            // Si no hay orden, solo seteamos la mesa y vamos al home
                            setActiveTable(table, null);
                            goto('/');
                        } else {
                            onAddMore();
                        }
                    }}>
                        <svelte:fragment slot="icon">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                            </svg>
                        </svelte:fragment>
                        Añadir
                    </Button>
                    <Button 
                        variant="primary" 
                        class="shadow-xl shadow-primary/30 gap-2" 
                        onclick={onCheckout}
                        disabled={isProcessing || !order || !order.items || order.items.length === 0}
                    >
                        Cobrar
                        <svelte:fragment slot="icon">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2z" />
                            </svg>
                        </svelte:fragment>
                    </Button>
                </div>

                <div class="mt-4 flex flex-col items-center gap-1">
                    {#if order}
                        <Button 
                            variant="ghost" 
                            size="sm" 
                            danger 
                            class="gap-2 opacity-60 hover:opacity-100" 
                            onclick={handleCancelOrDelete}
                            disabled={isProcessing}
                        >
                            <svelte:fragment slot="icon">
                                {#if order.items && order.items.length > 0}
                                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                                    </svg>
                                {:else}
                                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                    </svg>
                                {/if}
                            </svelte:fragment>
                            {order.items && order.items.length > 0 ? "Cancelar Pedido" : "Eliminar Vaciado"}
                        </Button>
                    {/if}

                    <Button 
                        variant="ghost" 
                        size="sm" 
                        class="gap-2 opacity-60 hover:opacity-100" 
                        onclick={handleVacate}
                        disabled={isProcessing}
                    >
                        <svelte:fragment slot="icon">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9" />
                            </svg>
                        </svelte:fragment>
                        Desocupar Mesa Sin Pagar
                    </Button>
                </div>
            </div>
        </div>
    </div>
{/if}
