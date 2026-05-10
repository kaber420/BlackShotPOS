<script lang="ts">
    import { onMount, onDestroy } from 'svelte';
    import { OrderService, type Order, OrderStatus } from '$lib/api/orders';
    import { KitchenService } from '$lib/api/kitchen';
    import { TableService, type Table } from '$lib/api/tables';
    import { printTicket, getRecommendedMethod, type PrintMethod } from '$lib/printer';
    import { can, appState, loadOrderToCart } from '$lib/app_state.svelte';
    import Button from '$lib/components/ui/Button.svelte';
    import OrderCard from '$lib/components/OrderCard.svelte';
    import { posSocket } from '$lib/pos_socket.svelte';

    let orders = $derived<Order[]>(posSocket.recentOrders);
    let isLoading = $state(true);
    let printingOrderId = $state<number | null>(null);
    let selectedMethod = $state<PrintMethod>('download');

    // Estado del modal de cancelación
    let cancellingOrder = $state<Order | null>(null);
    let cancelReason = $state("");
    let isCancelling = $state(false);

    // Estado del modal de transferencia
    let transferringOrder = $state<Order | null>(null);
    let freeTables = $state<Table[]>([]);
    let selectedTableId = $state<number | null>(null);
    let isTransferring = $state(false);

    // ── Filtros ──────────────────────────────────────────────────────────────────
    type FilterKey = 'active' | 'all' | 'PENDING' | 'PREPARING' | 'READY' | 'DELIVERED' | 'PAID' | 'CANCELLED';
    let activeFilter = $state<FilterKey>('active');

    const ACTIVE_STATUSES = new Set(['PENDING', 'PREPARING', 'READY']);

    onMount(async () => {
        posSocket.subscribe("recent_orders");
        
        // Carga inicial resiliente
        if (posSocket.recentOrders.length === 0) {
            isLoading = true;
            try {
                const data = await OrderService.getAll();
                // Si el socket aún no ha poblado los datos (ej. delay en WS), podemos poblarlos aquí
                if (posSocket.recentOrders.length === 0) {
                    posSocket.recentOrders = data.sort((a, b) => 
                        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
                    );
                }
            } catch (e) {
                console.error("Error al cargar órdenes iniciales:", e);
            } finally {
                isLoading = false;
            }
        } else {
            isLoading = false;
        }

        selectedMethod = getRecommendedMethod();
    });

    onDestroy(() => {
        posSocket.unsubscribe("recent_orders");
    });

    // Contadores por grupo
    let activeOrders    = $derived(orders.filter(o => ACTIVE_STATUSES.has(o.status) || (o.status === 'DELIVERED' && o.balance_due > 0) || (o.status === 'PAID' && o.balance_due > 0 /* solo en caso de errores */)));
    let pendingOrders   = $derived(orders.filter(o => o.status === 'PENDING'));
    let preparingOrders = $derived(orders.filter(o => o.status === 'PREPARING'));
    let readyOrders     = $derived(orders.filter(o => o.status === 'READY'));
    let deliveredOrders = $derived(orders.filter(o => (o.status === 'DELIVERED' && o.balance_due === 0) || o.status === 'PAID'));
    let cancelledOrders = $derived(orders.filter(o => o.status === 'CANCELLED'));

    let filteredOrders = $derived(
        activeFilter === 'active'    ? activeOrders :
        activeFilter === 'PENDING'   ? pendingOrders :
        activeFilter === 'PREPARING' ? preparingOrders :
        activeFilter === 'READY'     ? readyOrders :
        activeFilter === 'DELIVERED' ? deliveredOrders :
        activeFilter === 'CANCELLED' ? cancelledOrders :
        orders  // 'all'
    );

    // ── Helpers de estado ────────────────────────────────────────────────────────
    const orderStatusLabel: Record<string, string> = {
        PENDING:   'PENDIENTE',
        PREPARING: 'PREPARANDO',
        READY:     'LISTO',
        PAID:      'PAGADO',
        DELIVERED: 'ENTREGADO',
        CANCELLED: 'CANCELADO',
    };





    // ── Acciones ─────────────────────────────────────────────────────────────────

    /** Avanza el estado de un ítem individual (requiere permiso manageKitchenStatus) */
    async function handleItemAdvance(order: Order, item: any) {
        try {
            if (item.status === 'PENDING') {
                // Ahora hablamos directamente con Cocina para estados operativos
                await KitchenService.startPreparingItem(
                    item.id, 
                    appState.userUuid || "system", 
                    appState.userName || "Admin"
                );
            } else if (item.status === 'PREPARING') {
                await KitchenService.markItemAsReady(item.id);
            } else if (item.status === 'READY') {
                // Entregar sí es un estado comercial (Ventas)
                await OrderService.updateItemStatus(order.id, item.id, OrderStatus.DELIVERED);
            }
        } catch (e: any) {
            alert(`Error al actualizar platillo: ${e.message || e}`);
        }
    }

    /** Entrega todos los ítems que estén en estado READY */
    async function handleComplete(orderId: number) {
        try {
            const order = orders.find(o => o.id === orderId);
            if (!order) return;
            
            const readyItems = order.items?.filter(i => i.status === 'READY') || [];
            if (readyItems.length === 0) return;

            // En un sistema real, querríamos un endpoint de "batch update"
            // Por ahora, lo hacemos secuencial o en paralelo.
            await Promise.all(readyItems.map(item => 
                OrderService.updateItemStatus(orderId, item.id, OrderStatus.DELIVERED)
            ));

            // Si todos los ítems de la orden ya están entregados, forzamos actualización del estado global
            // (Aunque el backend ahora lo hace, esto asegura consistencia inmediata en la UI)
            const updatedOrder = orders.find(o => o.id === orderId);
            if (updatedOrder && updatedOrder.items.every(i => i.status === 'DELIVERED' || i.status === 'CANCELLED')) {
                await OrderService.updateStatus(orderId, OrderStatus.DELIVERED);
            }
        } catch (e) {
            alert(`Error al entregar listos: ${e}`);
        }
    }

    async function handleCancelOrDelete(order: Order) {
        const hasItems = order.items && order.items.length > 0;
        
        if (hasItems) {
            cancellingOrder = order;
            cancelReason = "";
        } else {
            if (!confirm("¿Estás seguro de que deseas ELIMINAR definitivamente este pedido vacío?")) return;
            try {
                await OrderService.delete(order.id);
            } catch (e) {
                alert(`Error: ${e}`);
            }
        }
    }

    async function confirmCancel() {
        if (!cancellingOrder || !cancelReason.trim()) return;
        isCancelling = true;
        try {
            await OrderService.cancelWithReason(cancellingOrder.id, cancelReason);
            cancellingOrder = null;
        } catch (e: any) {
            alert(`Error cancelando: ${e?.message ?? e}`);
        } finally {
            isCancelling = false;
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

    async function handleTransferOrderClick(order: Order) {
        transferringOrder = order;
        selectedTableId = null;
        try {
            const allTables = await TableService.getAll();
            freeTables = allTables.filter(t => t.status === 'Free');
        } catch (e) {
            console.error("Error al cargar mesas:", e);
            alert("No se pudieron cargar las mesas.");
        }
    }

    async function confirmTransfer() {
        if (!transferringOrder || !selectedTableId) return;
        isTransferring = true;
        try {
            await OrderService.transfer(transferringOrder.id, selectedTableId);
            transferringOrder = null;
        } catch (e: any) {
            alert(`Error transfiriendo mesa: ${e?.message ?? e}`);
        } finally {
            isTransferring = false;
        }
    }

    function openCartForCharge(order: Order) {
        loadOrderToCart(order);
        appState.cartVisible = true;
    }

    function calculateTotal(order: Order) {
        return order.items?.reduce((sum, item) => sum + (item.unit_price * item.quantity), 0) || 0;
    }

    let searchQuery = $state('');
    let filteredBySearch = $derived(
        searchQuery.trim() === '' 
            ? filteredOrders 
            : filteredOrders.filter(o => 
                o.id.toString().includes(searchQuery) || 
                o.table_number?.toString().includes(searchQuery) ||
                o.customer_name?.toLowerCase().includes(searchQuery.toLowerCase())
            )
    );
</script>

<div class="p-6 md:p-8 lg:p-10 flex flex-col gap-8 w-full flex-1 min-h-0 overflow-y-auto">
    <!-- ── Header ──────────────────────────────────────────────────────────── -->
    <header class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div class="flex flex-col gap-1">
            <h1 class="text-4xl font-extrabold tracking-tight">Órdenes Recientes</h1>
            <p class="text-lg opacity-70">Seguimiento en tiempo real del estado de cada platillo.</p>
        </div>


    </header>

    <!-- ── Filtros y Búsqueda ────────────────────────────────────────────────── -->
    <div class="flex flex-col md:flex-row gap-4 items-center justify-between">
        <div class="flex flex-col md:flex-row gap-4 w-full md:w-auto items-center">
            <!-- Barra de Búsqueda -->
            <div class="relative w-full md:w-80 group">
                <div class="absolute inset-y-0 left-0 pl-5 flex items-center pointer-events-none">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 opacity-20 group-focus-within:opacity-100 group-focus-within:text-primary transition-all" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                </div>
                <input 
                    type="text" 
                    bind:value={searchQuery}
                    placeholder="Buscar por # o mesa..." 
                    class="input input-lg w-full pl-14 bg-base-100 border-2 border-base-200 rounded-[1.5rem] font-bold focus:border-primary/50 transition-all shadow-sm"
                />
            </div>

            <!-- Dropdown de Filtro (ESTILO INVENTARIO) -->
            <div class="dropdown dropdown-bottom">
                <div tabindex="0" role="button" class="btn btn-lg bg-base-100 border-2 border-base-200 px-6 font-black flex items-center gap-2 hover:border-primary/30 transition-all rounded-[1.5rem] shadow-sm">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                    </svg>
                    Filtrar: 
                    <span class="text-primary">
                        {activeFilter === 'active' ? 'Activas' :
                        activeFilter === 'PENDING' ? 'Pendientes' :
                        activeFilter === 'PREPARING' ? 'En Cocina' :
                        activeFilter === 'READY' ? 'Listos' :
                        activeFilter === 'DELIVERED' ? 'Historial' :
                        activeFilter === 'CANCELLED' ? 'Canceladas' : 'Todas'}
                    </span>
                </div>
                <div tabindex="0" class="dropdown-content z-[50] card card-compact w-64 p-2 shadow-2xl bg-base-100 border border-base-200 mt-3 rounded-2xl">
                    <div class="p-3 border-b border-base-200 mb-2 flex justify-between items-center">
                        <span class="text-[10px] uppercase font-black opacity-40 tracking-widest">Estado de Orden</span>
                    </div>
                    <div class="max-h-60 overflow-y-auto space-y-1 p-1">
                        <button class="w-full text-left p-3 rounded-xl hover:bg-base-200 transition-colors font-bold text-sm {activeFilter === 'active' ? 'bg-primary/10 text-primary' : ''}" onclick={() => activeFilter = 'active'}>
                            Activas
                        </button>
                        <button class="w-full text-left p-3 rounded-xl hover:bg-base-200 transition-colors font-bold text-sm {activeFilter === 'PENDING' ? 'bg-warning/10 text-warning' : ''}" onclick={() => activeFilter = 'PENDING'}>
                            Pendientes
                        </button>
                        <button class="w-full text-left p-3 rounded-xl hover:bg-base-200 transition-colors font-bold text-sm {activeFilter === 'PREPARING' ? 'bg-primary/10 text-primary' : ''}" onclick={() => activeFilter = 'PREPARING'}>
                            En Cocina (Preparando)
                        </button>
                        <button class="w-full text-left p-3 rounded-xl hover:bg-base-200 transition-colors font-bold text-sm {activeFilter === 'READY' ? 'bg-success/10 text-success' : ''}" onclick={() => activeFilter = 'READY'}>
                            Listos
                        </button>
                        <button class="w-full text-left p-3 rounded-xl hover:bg-base-200 transition-colors font-bold text-sm {activeFilter === 'DELIVERED' ? 'bg-neutral/10 text-neutral' : ''}" onclick={() => activeFilter = 'DELIVERED'}>
                            Historial (Entregadas/Pagadas)
                        </button>
                        <button class="w-full text-left p-3 rounded-xl hover:bg-base-200 transition-colors font-bold text-sm {activeFilter === 'CANCELLED' ? 'bg-error/10 text-error' : ''}" onclick={() => activeFilter = 'CANCELLED'}>
                            Canceladas
                        </button>
                        <div class="border-t border-base-200 my-1"></div>
                        <button class="w-full text-left p-3 rounded-xl hover:bg-base-200 transition-colors font-bold text-sm {activeFilter === 'all' ? 'bg-base-300' : ''}" onclick={() => activeFilter = 'all'}>
                            Todas
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- ── Contenido ───────────────────────────────────────────────────────── -->
    {#if isLoading}
        <div class="flex justify-center py-20">
            <span class="loading loading-spinner loading-lg text-primary"></span>
        </div>
    {:else if filteredOrders.length === 0}
        <div class="flex flex-col items-center justify-center py-20 bg-base-200 rounded-2xl border-2 border-dashed border-base-300 gap-2">
            <p class="text-5xl opacity-20">
                {activeFilter === 'active' ? '✅' : activeFilter === 'DELIVERED' ? '📋' : activeFilter === 'CANCELLED' ? '🚫' : '🗂'}
            </p>
            <p class="text-xl font-bold opacity-30 italic">
                {activeFilter === 'active'    ? '¡Todo tranquilo! Sin órdenes activas.' :
                 activeFilter === 'DELIVERED' ? 'No hay órdenes entregadas aún.' :
                 activeFilter === 'CANCELLED' ? 'No hay órdenes canceladas.' :
                 activeFilter === 'PENDING'   ? 'Sin órdenes pendientes.' :
                 activeFilter === 'PREPARING' ? 'Nada en preparación ahora.' :
                 activeFilter === 'READY'     ? 'No hay órdenes listas para entregar.' :
                 'No hay órdenes registradas.'}
            </p>
        </div>
    {:else}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-6">
            {#each filteredBySearch as order (order.id)}
                <OrderCard
                    {order}
                    view="orders"
                    canManageKitchenStatus={can.manageKitchenStatus()}
                    {printingOrderId}
                    onItemComplete={handleItemAdvance}
                    onCancelOrder={handleCancelOrDelete}
                    onTransferOrder={handleTransferOrderClick}
                    onPrint={handlePrintTicket}
                    onCharge={can.charge() ? openCartForCharge : undefined}
                    onDeliver={can.charge() ? handleComplete : undefined}
                />
            {/each}
        </div>
    {/if}
</div>

{#if cancellingOrder}
<div class="modal modal-open bg-base-300/80 backdrop-blur-sm z-50">
    <div class="modal-box shadow-2xl border border-error/20">
        <h3 class="font-black text-2xl text-error flex items-center gap-2 mb-2">
            Cancelar Pedido #{cancellingOrder.id}
        </h3>
        <p class="py-2 text-base-content/80 font-medium leading-tight">
            Estás a punto de cancelar un pedido con artículos cargados. Para completar la cancelación, es obligatorio escribir un motivo que será guardado en el <strong>registro de auditoría</strong>.
        </p>

        <div class="form-control w-full mt-4">
            <label class="label">
                <span class="label-text font-bold text-sm">Motivo exacto de la cancelación</span>
            </label>
            <textarea
                class="textarea textarea-bordered textarea-error w-full text-base"
                rows="3"
                placeholder="Ej. El cliente se retiró antes de pagar, Error al tomar la orden, etc."
                bind:value={cancelReason}
            ></textarea>
        </div>

        <div class="modal-action mt-6 flex justify-end gap-3">
            <Button variant="ghost" class="border border-base-300 text-base-content/70" onclick={() => cancellingOrder = null} disabled={isCancelling}>
                Volver
            </Button>
            <Button variant="danger" class="shadow-xl" onclick={confirmCancel} disabled={!cancelReason.trim()} isLoading={isCancelling}>
                Confirmar Cancelación
            </Button>
        </div>
    </div>
</div>
{/if}

{#if transferringOrder}
<div class="modal modal-open bg-base-300/80 backdrop-blur-sm z-50">
    <div class="modal-box shadow-2xl border border-primary/20">
        <h3 class="font-black text-2xl text-primary flex items-center gap-2 mb-2">
            Mover Mesa - Pedido #{transferringOrder.id}
        </h3>
        <p class="py-2 text-base-content/80 font-medium leading-tight mb-2">
            Selecciona la nueva mesa a la que se mudarán los clientes. Solo se muestran las mesas que están actualmente libres.
        </p>

        <div class="grid grid-cols-3 gap-3 max-h-60 overflow-y-auto p-1">
            {#if freeTables.length === 0}
                <div class="col-span-3 text-center py-4 text-base-content/50 italic">
                    No hay mesas libres disponibles.
                </div>
            {:else}
                {#each freeTables as t}
                    <button 
                        class="btn btn-outline {selectedTableId === t.id ? 'btn-primary bg-primary/10' : 'border-base-300'}" 
                        onclick={() => selectedTableId = t.id}
                    >
                        Mesa {t.number}
                    </button>
                {/each}
            {/if}
        </div>

        <div class="modal-action mt-6 flex justify-end gap-3">
            <Button variant="ghost" class="border border-base-300 text-base-content/70" onclick={() => transferringOrder = null} disabled={isTransferring}>
                Cancelar
            </Button>
            <Button variant="primary" class="shadow-xl" onclick={confirmTransfer} disabled={!selectedTableId || isTransferring} isLoading={isTransferring}>
                Confirmar Traslado
            </Button>
        </div>
    </div>
</div>
{/if}

