<script lang="ts">
    import { onMount, onDestroy } from 'svelte';
    import { OrderService, type Order, OrderStatus } from '$lib/api/orders';
    import { printTicket, getRecommendedMethod, type PrintMethod } from '$lib/printer';

    let orders = $state<Order[]>([]);
    let isLoading = $state(true);
    let interval: any;
    let printingOrderId = $state<number | null>(null);
    let selectedMethod = $state<PrintMethod>('download');

    onMount(async () => {
        await loadOrders();
        interval = setInterval(loadOrders, 15000);
        selectedMethod = getRecommendedMethod();
    });

    onDestroy(() => {
        if (interval) clearInterval(interval);
    });

    async function loadOrders() {
        try {
            // Cargar todas las órdenes (paginación o filtros podrían agregarse luego)
            orders = await OrderService.getAll();
            // Ordenar por las más recientes primero
            orders = orders.sort((a, b) => 
                new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
            );
        } catch (e) {
            console.error("Error loading orders", e);
        } finally {
            isLoading = false;
        }
    }

    let dineInOrders = $derived(orders.filter(o => o.type === 'DINE_IN'));
    let takeawayOrders = $derived(orders.filter(o => o.type === 'TAKEAWAY' || o.type === 'DELIVERY'));

    function getStatusBadge(status: string) {
        switch (status) {
            case 'PENDING': return 'badge-warning';
            case 'PREPARING': return 'badge-primary';
            case 'READY': return 'badge-success';
            case 'PAID': return 'badge-neutral';
            case 'DELIVERED': return 'badge-ghost opacity-70';
            case 'CANCELLED': return 'badge-error';
            default: return 'badge-ghost';
        }
    }

    async function handleComplete(orderId: number) {
        try {
            await OrderService.updateStatus(orderId, OrderStatus.DELIVERED);
            await loadOrders();
        } catch (e) {
            alert(`Error al entregar: ${e}`);
        }
    }

    async function handlePrintTicket(orderId: number) {
        printingOrderId = orderId;
        try {
            await printTicket(orderId, selectedMethod);
        } catch (e: any) {
            alert(`Error al imprimir pedido: ${e?.message}`);
        } finally {
            printingOrderId = null;
        }
    }

    function calculateTotal(order: Order) {
        return order.items?.reduce((sum, item) => sum + (item.unit_price * item.quantity), 0) || 0;
    }
</script>

<div class="p-6 md:p-8 lg:p-12 max-w-7xl mx-auto flex flex-col gap-8">
    <header class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div class="flex flex-col gap-2">
            <h1 class="text-4xl font-extrabold tracking-tight">Órdenes Recientes</h1>
            <p class="text-lg opacity-70">Seguimiento de pedidos y estado de ventas.</p>
        </div>
        
        <button class="btn btn-neutral btn-md gap-2 border-none bg-[#2c3e50] hover:bg-[#1a252f] text-white font-bold shadow-lg">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c1.097 0 2.16.192 3.142.546m0-12.5a8.967 8.967 0 016 0m0 12.5a11.515 11.515 0 01-3.142-.546M12 6.042V18" /></svg>
            Ver Reporte de Ventas
        </button>
    </header>

    <div class="tabs tabs-boxed bg-base-200/50 p-1 w-fit mb-4">
        <button class="tab tab-active font-bold">Todas ({orders.length})</button>
        <button class="tab">Comedor ({dineInOrders.length})</button>
        <button class="tab">Para Llevar ({takeawayOrders.length})</button>
    </div>

    {#if isLoading}
        <div class="flex justify-center py-20">
            <span class="loading loading-spinner loading-lg text-primary"></span>
        </div>
    {:else if orders.length === 0}
        <div class="flex flex-col items-center justify-center py-20 bg-base-200 rounded-2xl border-2 border-dashed border-base-300">
            <p class="text-xl font-bold opacity-30 italic">No hay órdenes registradas</p>
        </div>
    {:else}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {#each orders as order}
                <div class="card bg-base-100 shadow-md hover:shadow-xl transition-shadow border-t-8 { order.status === 'PAID' ? 'border-neutral' : 'border-primary'}">
                    <div class="card-body p-6">
                        <div class="flex justify-between items-start mb-2">
                            <div class="flex flex-col gap-1">
                                <span class="text-xs font-black uppercase tracking-widest opacity-50 px-2 py-1 bg-base-200 rounded w-fit">#{order.id}</span>
                                {#if order.is_paid}
                                    <span class="badge badge-success badge-xs font-black text-[9px] border-none">PAGADO</span>
                                {/if}
                            </div>
                            <span class="badge badge-sm font-bold {getStatusBadge(order.status)}">{order.status === 'DELIVERED' ? 'ENTREGADO' : order.status}</span>
                        </div>
                        <h3 class="text-xl font-bold">
                            {order.table_id ? `Mesa ${order.table_id}` : 'Mostrador'}
                        </h3>
                        <p class="text-xs opacity-60 uppercase font-black tracking-tight mt-1">
                            {order.type} • {new Date(order.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                        </p>
                        
                        <div class="mt-4 pt-4 border-t border-base-200 flex justify-between items-center">
                            <span class="font-mono text-lg font-black text-primary">
                                ${calculateTotal(order).toFixed(2)}
                            </span>
                            <div class="flex gap-1">
                                {#if order.status === 'READY' && order.is_paid}
                                    <button 
                                        class="btn btn-success btn-sm font-bold shadow-sm"
                                        onclick={() => handleComplete(order.id)}
                                    >
                                        Entregar
                                    </button>
                                {:else if order.status === 'READY' && !order.is_paid}
                                    <a 
                                        href="/?order_id={order.id}" 
                                        class="btn btn-primary btn-sm font-bold shadow-sm"
                                    >
                                        Cobrar y Entregar
                                    </a>
                                {:else if order.status !== 'PAID' && order.status !== 'DELIVERED' && order.status !== 'CANCELLED' && !order.is_paid}
                                    <a 
                                        href="/?order_id={order.id}" 
                                        class="btn btn-primary btn-sm font-bold shadow-sm"
                                    >
                                        Cobrar
                                    </a>
                                {/if}
                                <!-- Botón de impresión de ticket -->
                                <button
                                    class="btn btn-ghost btn-sm"
                                    onclick={() => handlePrintTicket(order.id)}
                                    disabled={printingOrderId === order.id}
                                    title="Imprimir Pedido"
                                    id="print-ticket-{order.id}"
                                    aria-label="Imprimir pedido de la orden {order.id}"
                                >
                                    {#if printingOrderId === order.id}
                                        <span class="loading loading-spinner loading-xs"></span>
                                    {:else}
                                        🖨️
                                    {/if}
                                </button>
                                <button class="btn btn-ghost btn-sm text-primary font-bold">Detalle</button>
                            </div>
                        </div>
                    </div>
                </div>
            {/each}
        </div>
    {/if}
</div>
