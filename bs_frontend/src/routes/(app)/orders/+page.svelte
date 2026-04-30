<script lang="ts">
    import { onMount, onDestroy } from 'svelte';
    import { OrderService, type Order, OrderStatus } from '$lib/api/orders';
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
    // 'active' = órdenes que requieren atención (por defecto)
    // Un string de OrderStatus = filtrar por ese estado específico
    // 'all' = todas (para consultas/reclamaciones)
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
                await OrderService.updateItemStatus(order.id, item.id, OrderStatus.PREPARING);
            } else if (item.status === 'PREPARING') {
                await OrderService.updateItemStatus(order.id, item.id, OrderStatus.READY);
            } else if (item.status === 'READY') {
                await OrderService.updateItemStatus(order.id, item.id, OrderStatus.DELIVERED);
            }
        } catch (e) {
            alert(`Error al actualizar platillo: ${e}`);
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
</script>

<div class="p-6 md:p-8 lg:p-10 flex flex-col gap-8 w-full flex-1 min-h-0 overflow-y-auto">
    <!-- ── Header ──────────────────────────────────────────────────────────── -->
    <header class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div class="flex flex-col gap-1">
            <h1 class="text-4xl font-extrabold tracking-tight">Órdenes Recientes</h1>
            <p class="text-lg opacity-70">Seguimiento en tiempo real del estado de cada platillo.</p>
        </div>

        <Button variant="neutral" size="md" class="gap-2 border-none bg-[#2c3e50] hover:bg-[#1a252f] text-white shadow-lg">
            <svelte:fragment slot="icon">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c1.097 0 2.16.192 3.142.546m0-12.5a8.967 8.967 0 016 0m0 12.5a11.515 11.515 0 01-3.142-.546M12 6.042V18" /></svg>
            </svelte:fragment>
            Ver Reporte de Ventas
        </Button>
    </header>

    <!-- ── Filtros ─────────────────────────────────────────────────────────── -->
    <div class="flex flex-col gap-3">

        <!-- Vista principal: Activas / Historial / Todas -->
        <div class="flex flex-wrap gap-2 items-center">
            <!-- Activas (por defecto) -->
            <Button
                id="filter-active"
                variant={activeFilter === 'active' ? 'primary' : 'ghost'}
                size="sm"
                class="gap-2 {activeFilter !== 'active' ? 'border border-base-300' : 'shadow-md shadow-primary/20'}"
                onclick={() => activeFilter = 'active'}
            >
                <span class="relative flex h-2 w-2">
                    {#if activeOrders.length > 0}
                        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-current opacity-60"></span>
                    {/if}
                    <span class="relative inline-flex rounded-full h-2 w-2 bg-current"></span>
                </span>
                Activas
                <span class="badge badge-sm {activeFilter === 'active' ? 'badge-primary-content bg-white/20 text-white border-none' : 'badge-ghost'}">
                    {activeOrders.length}
                </span>
            </Button>

            <!-- Historial (entregadas + pagadas) -->
            <Button
                id="filter-history"
                variant={activeFilter === 'DELIVERED' ? 'neutral' : 'ghost'}
                size="sm"
                class="gap-2 {activeFilter !== 'DELIVERED' ? 'border border-base-300' : 'shadow-md'}"
                onclick={() => activeFilter = 'DELIVERED'}
            >
                📋 Historial
                <span class="badge badge-sm badge-ghost">{deliveredOrders.length}</span>
            </Button>

            <!-- Canceladas -->
            <Button
                id="filter-cancelled"
                variant={activeFilter === 'CANCELLED' ? 'danger' : 'ghost'}
                size="sm"
                class="gap-2 {activeFilter !== 'CANCELLED' ? 'border border-base-300' : 'shadow-md'}"
                onclick={() => activeFilter = 'CANCELLED'}
            >
                🚫 Canceladas
                <span class="badge badge-sm badge-ghost">{cancelledOrders.length}</span>
            </Button>

            <!-- Separador -->
            <div class="h-6 w-px bg-base-300 mx-1 hidden md:block"></div>

            <!-- Todas (para búsqueda / reclamaciones) -->
            <Button
                id="filter-all"
                variant="ghost"
                size="sm"
                class="gap-2 {activeFilter === 'all' ? 'border-primary' : 'border-base-300'} border opacity-70"
                onclick={() => activeFilter = 'all'}
            >
                🗂 Todas ({orders.length})
            </Button>
        </div>

        <!-- Chips de sub-filtro: solo en vista Activas para afinar -->
        {#if activeFilter === 'active' || activeFilter === 'PENDING' || activeFilter === 'PREPARING' || activeFilter === 'READY'}
            <div class="flex flex-wrap gap-2 items-center pl-1">
                <span class="text-[10px] uppercase tracking-widest font-black opacity-40 mr-1">Filtrar por:</span>

                <!-- Todas las activas -->
                <Button
                    variant={activeFilter === 'active' ? 'primary' : 'outline'}
                    size="sm"
                    class="rounded-full"
                    onclick={() => activeFilter = 'active'}
                >
                    Todas las activas ({activeOrders.length})
                </Button>

                <!-- Pendientes -->
                <Button
                    variant={activeFilter === 'PENDING' ? 'warning' : 'outline'}
                    size="sm"
                    class="rounded-full"
                    onclick={() => activeFilter = 'PENDING'}
                >
                    ⏳ Pendiente ({pendingOrders.length})
                </Button>

                <!-- Preparando -->
                <Button
                    variant={activeFilter === 'PREPARING' ? 'primary' : 'outline'}
                    size="sm"
                    class="rounded-full"
                    onclick={() => activeFilter = 'PREPARING'}
                >
                    🍳 Preparando ({preparingOrders.length})
                </Button>

                <!-- Listos -->
                <Button
                    variant={activeFilter === 'READY' ? 'success' : 'outline'}
                    size="sm"
                    class="rounded-full"
                    onclick={() => activeFilter = 'READY'}
                >
                    ✅ Listos ({readyOrders.length})
                </Button>
            </div>
        {/if}
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
            {#each filteredOrders as order (order.id)}
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

