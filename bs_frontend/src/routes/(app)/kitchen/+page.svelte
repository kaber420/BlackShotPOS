<script lang="ts">
    import { onMount, onDestroy } from 'svelte';
    import { OrderService, OrderStatus, type Order } from '$lib/api/orders';
    import { TableService, type Table } from '$lib/api/tables';

    let orders = $state<Order[]>([]);
    let tables = $state<Table[]>([]);
    let isLoading = $state(true);
    let interval: any;

    onMount(async () => {
        await Promise.all([loadOrders(), loadTables()]);
        
        // Polling cada 10 segundos
        interval = setInterval(loadOrders, 10000);
    });

    onDestroy(() => {
        if (interval) clearInterval(interval);
    });

    async function loadOrders() {
        try {
            // Cargar órdenes pendientes y en preparación
            const [pending, preparing] = await Promise.all([
                OrderService.getAll(OrderStatus.PENDING),
                OrderService.getAll(OrderStatus.PREPARING)
            ]);
            orders = [...pending, ...preparing].sort((a, b) => 
                new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
            );
        } catch (e) {
            console.error("Error loading kitchen orders", e);
        } finally {
            isLoading = false;
        }
    }

    async function loadTables() {
        try {
            tables = await TableService.getAll();
        } catch (e) {
            console.error("Error loading tables", e);
        }
    }

    async function handleComplete(order: Order) {
        try {
            // Primero pasar a PREPARING si estaba PENDING (para disparar inventario si el backend así lo requiere)
            if (order.status === OrderStatus.PENDING) {
                await OrderService.updateStatus(order.id, OrderStatus.PREPARING);
            }
            // Luego pasar a READY
            await OrderService.updateStatus(order.id, OrderStatus.READY);
            await loadOrders();
        } catch (e) {
            alert(`Error al completar orden: ${e}`);
        }
    }

    function getTableNumber(tableId?: number) {
        if (!tableId) return 'MOSTRADOR';
        const table = tables.find(t => t.id === tableId);
        return table ? `MESA ${table.number}` : `ID: ${tableId}`;
    }

    function getTimeAgo(dateStr: string) {
        const now = new Date();
        const date = new Date(dateStr);
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        return `${diffMins} mins`;
    }
</script>

<div class="p-6 md:p-8 lg:p-12 max-w-7xl mx-auto flex flex-col gap-8">
    <header class="flex flex-col gap-2">
        <div class="flex justify-between items-center">
            <div>
                <h1 class="text-4xl font-extrabold tracking-tight">Cocina (KDS)</h1>
                <p class="text-lg opacity-70">Control de comandas y tiempos de preparación.</p>
            </div>
            <div class="flex gap-2">
                {#if !isLoading}
                    <div class="badge badge-outline gap-2 p-4">
                        <span class="relative flex h-2 w-2">
                            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75"></span>
                            <span class="relative inline-flex rounded-full h-2 w-2 bg-success"></span>
                        </span>
                        EN VIVO
                    </div>
                {/if}
                <button class="btn btn-ghost btn-circle" onclick={loadOrders} aria-label="Recargar comandas">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                </button>
            </div>
        </div>
    </header>

    {#if isLoading}
        <div class="flex justify-center py-20">
            <span class="loading loading-spinner loading-lg text-primary"></span>
        </div>
    {:else if orders.length === 0}
        <div class="flex flex-col items-center justify-center py-20 bg-base-200 rounded-2xl border-2 border-dashed border-base-300">
            <p class="text-2xl font-bold opacity-20 italic">No hay comandas activas</p>
            <p class="text-sm opacity-10 mt-2">Los pedidos aparecerán aquí automáticamente.</p>
        </div>
    {:else}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {#each orders as order}
                <div class="card bg-base-100 shadow-xl border-l-4 { order.status === 'PENDING' ? 'border-warning' : 'border-primary' } flex flex-col">
                    <div class="card-body p-6 flex flex-col h-full">
                        <div class="flex justify-between items-start mb-4">
                            <div>
                                <h2 class="card-title text-2xl font-bold">Orden #{order.id}</h2>
                                <p class="text-xs font-bold uppercase tracking-widest opacity-60">
                                    {getTableNumber(order.table_id)} • {getTimeAgo(order.created_at)}
                                </p>
                            </div>
                            <div class="badge { order.status === 'PENDING' ? 'badge-warning' : 'badge-primary' } font-bold p-3">
                                {order.status === 'PENDING' ? 'PENDIENTE' : 'PREPARANDO'}
                            </div>
                        </div>

                        <div class="space-y-2 mb-6 flex-grow">
                            {#if order.items}
                                {#each order.items as item}
                                    <div class="flex flex-col bg-base-200/50 p-3 rounded-lg border border-base-300/50">
                                        <div class="flex justify-between items-center">
                                            <span class="font-bold text-lg">{item.quantity}x {item.product?.name || 'Producto'}</span>
                                        </div>
                                        {#if item.modifiers && item.modifiers.length > 0}
                                            <div class="flex flex-wrap gap-1 mt-1">
                                                {#each item.modifiers as mod}
                                                    <span class="badge badge-sm badge-outline opacity-70">{mod.name}</span>
                                                {/each}
                                            </div>
                                        {/if}
                                    </div>
                                {/each}
                            {/if}
                        </div>

                        {#if order.external_reference}
                            <p class="text-[10px] text-accent font-bold mb-4">REF: {order.external_reference}</p>
                        {/if}

                        <div class="card-actions justify-end mt-auto pt-4 border-t border-base-200">
                            <button 
                                class="btn { order.status === 'PENDING' ? 'btn-outline border-primary' : 'btn-primary' } btn-block text-lg"
                                onclick={() => handleComplete(order)}
                            >
                                {order.status === 'PENDING' ? 'Empezar' : 'Listo'}
                            </button>
                        </div>
                    </div>
                </div>
            {/each}
        </div>
    {/if}
</div>
