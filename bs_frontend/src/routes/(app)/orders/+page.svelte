<script lang="ts">
    import { onMount, onDestroy } from 'svelte';
    import { OrderService, type Order, OrderStatus } from '$lib/api/orders';
    import { printTicket, getRecommendedMethod, type PrintMethod } from '$lib/printer';
    import { can, appState, loadOrderToCart } from '$lib/app_state.svelte';

    let orders = $state<Order[]>([]);
    let isLoading = $state(true);
    let printingOrderId = $state<number | null>(null);
    let selectedMethod = $state<PrintMethod>('download');
    let ws: WebSocket | null = null;
    let isDestroyed = false;

    // Estado del modal de cancelación
    let cancellingOrder = $state<Order | null>(null);
    let cancelReason = $state("");
    let isCancelling = $state(false);

    // ── Filtros ──────────────────────────────────────────────────────────────────
    // 'active' = órdenes que requieren atención (por defecto)
    // Un string de OrderStatus = filtrar por ese estado específico
    // 'all' = todas (para consultas/reclamaciones)
    type FilterKey = 'active' | 'all' | 'PENDING' | 'PREPARING' | 'READY' | 'DELIVERED' | 'PAID' | 'CANCELLED';
    let activeFilter = $state<FilterKey>('active');

    const ACTIVE_STATUSES = new Set(['PENDING', 'PREPARING', 'READY']);

    onMount(() => {
        connectWebSocket();
        selectedMethod = getRecommendedMethod();
    });

    onDestroy(() => {
        isDestroyed = true;
        if (ws) ws.close();
    });

    function connectWebSocket() {
        if (typeof window === 'undefined' || isDestroyed) return;

        const token = localStorage.getItem('X-Omni-Token') || '';
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const url = `${protocol}//${host}/api/v1/pos/ws/pos?token=${encodeURIComponent(token)}`;

        ws = new WebSocket(url);

        ws.onopen = () => {
            console.log("🔌 Lista de Órdenes WS conectado");
            ws?.send(JSON.stringify({ action: "subscribe", topic: "recent_orders" }));
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (!data.error) {
                    orders = data;
                    isLoading = false;
                }
            } catch (e) {
                console.error("Error parseando datos WebSocket", e);
            }
        };

        ws.onclose = () => {
            if (isDestroyed) return;
            console.log("🔌 Lista de Órdenes WS desconectado. Reconectando en 5s...");
            setTimeout(connectWebSocket, 5000);
        };
    }

    // Contadores por grupo
    let activeOrders    = $derived(orders.filter(o => ACTIVE_STATUSES.has(o.status)));
    let pendingOrders   = $derived(orders.filter(o => o.status === 'PENDING'));
    let preparingOrders = $derived(orders.filter(o => o.status === 'PREPARING'));
    let readyOrders     = $derived(orders.filter(o => o.status === 'READY'));
    let deliveredOrders = $derived(orders.filter(o => o.status === 'DELIVERED' || o.status === 'PAID'));
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

    const itemStatusConfig: Record<string, { label: string; cls: string; dotCls: string }> = {
        PENDING:   { label: 'En cola',       cls: 'text-warning',  dotCls: 'bg-warning' },
        PREPARING: { label: 'Preparando',    cls: 'text-primary',  dotCls: 'bg-primary animate-pulse' },
        READY:     { label: 'Listo ✓',       cls: 'text-success',  dotCls: 'bg-success' },
        CANCELLED: { label: 'Anulado',       cls: 'text-error',    dotCls: 'bg-error' },
    };



    function getStatusBadgeClass(status: string) {
        switch (status) {
            case 'PENDING':   return 'badge-warning';
            case 'PREPARING': return 'badge-primary';
            case 'READY':     return 'badge-success';
            case 'PAID':      return 'badge-neutral';
            case 'DELIVERED': return 'badge-ghost opacity-70';
            case 'CANCELLED': return 'badge-error';
            default:          return 'badge-ghost';
        }
    }

    /** Porcentaje de ítems listos (excluye cancelados del denominador) */
    function getOrderProgress(order: Order) {
        const items = order.items ?? [];
        const active = items.filter(i => i.status !== 'CANCELLED');
        if (active.length === 0) return 100;
        const done = active.filter(i => i.status === 'READY').length;
        return Math.round((done / active.length) * 100);
    }

    // ── Acciones ─────────────────────────────────────────────────────────────────

    /** Avanza el estado de un ítem individual (requiere permiso manageKitchenStatus) */
    async function handleItemAdvance(order: Order, item: any) {
        try {
            if (item.status === 'PENDING') {
                await OrderService.updateItemStatus(order.id, item.id, OrderStatus.PREPARING);
            } else if (item.status === 'PREPARING') {
                await OrderService.updateItemStatus(order.id, item.id, OrderStatus.READY);
            }
        } catch (e) {
            alert(`Error al actualizar platillo: ${e}`);
        }
    }

    async function handleComplete(orderId: number) {
        try {
            await OrderService.updateStatus(orderId, OrderStatus.DELIVERED);
        } catch (e) {
            alert(`Error al entregar: ${e}`);
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

    function openCartForCharge(order: Order) {
        loadOrderToCart(order);
        appState.cartVisible = true;
    }

    function calculateTotal(order: Order) {
        return order.items?.reduce((sum, item) => sum + (item.unit_price * item.quantity), 0) || 0;
    }

    function getTimeAgo(dateStr: string) {
        const diffMins = Math.floor((Date.now() - new Date(dateStr).getTime()) / 60000);
        if (diffMins < 1) return 'ahora';
        if (diffMins < 60) return `${diffMins} min`;
        return `${Math.floor(diffMins / 60)}h ${diffMins % 60}m`;
    }
</script>

<div class="p-6 md:p-8 lg:p-12 max-w-7xl mx-auto flex flex-col gap-8 w-full flex-1 min-h-0 overflow-y-auto w-full">
    <!-- ── Header ──────────────────────────────────────────────────────────── -->
    <header class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div class="flex flex-col gap-1">
            <h1 class="text-4xl font-extrabold tracking-tight">Órdenes Recientes</h1>
            <p class="text-lg opacity-70">Seguimiento en tiempo real del estado de cada platillo.</p>
        </div>

        <button class="btn btn-neutral btn-md gap-2 border-none bg-[#2c3e50] hover:bg-[#1a252f] text-white font-bold shadow-lg">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c1.097 0 2.16.192 3.142.546m0-12.5a8.967 8.967 0 016 0m0 12.5a11.515 11.515 0 01-3.142-.546M12 6.042V18" /></svg>
            Ver Reporte de Ventas
        </button>
    </header>

    <!-- ── Filtros ─────────────────────────────────────────────────────────── -->
    <div class="flex flex-col gap-3">

        <!-- Vista principal: Activas / Historial / Todas -->
        <div class="flex flex-wrap gap-2 items-center">
            <!-- Activas (por defecto) -->
            <button
                id="filter-active"
                class="btn btn-sm gap-2 font-bold {activeFilter === 'active' ? 'btn-primary shadow-md shadow-primary/20' : 'btn-ghost border border-base-300'}"
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
            </button>

            <!-- Historial (entregadas + pagadas) -->
            <button
                id="filter-history"
                class="btn btn-sm gap-2 {activeFilter === 'DELIVERED' ? 'btn-neutral shadow-md' : 'btn-ghost border border-base-300'}"
                onclick={() => activeFilter = 'DELIVERED'}
            >
                📋 Historial
                <span class="badge badge-sm badge-ghost">{deliveredOrders.length}</span>
            </button>

            <!-- Canceladas -->
            <button
                id="filter-cancelled"
                class="btn btn-sm gap-2 {activeFilter === 'CANCELLED' ? 'btn-error shadow-md' : 'btn-ghost border border-base-300'}"
                onclick={() => activeFilter = 'CANCELLED'}
            >
                🚫 Canceladas
                <span class="badge badge-sm badge-ghost">{cancelledOrders.length}</span>
            </button>

            <!-- Separador -->
            <div class="h-6 w-px bg-base-300 mx-1 hidden md:block"></div>

            <!-- Todas (para búsqueda / reclamaciones) -->
            <button
                id="filter-all"
                class="btn btn-sm gap-2 {activeFilter === 'all' ? 'btn-ghost border-primary border' : 'btn-ghost border border-base-300'} opacity-70"
                onclick={() => activeFilter = 'all'}
            >
                🗂 Todas ({orders.length})
            </button>
        </div>

        <!-- Chips de sub-filtro: solo en vista Activas para afinar -->
        {#if activeFilter === 'active' || activeFilter === 'PENDING' || activeFilter === 'PREPARING' || activeFilter === 'READY'}
            <div class="flex flex-wrap gap-2 items-center pl-1">
                <span class="text-[10px] uppercase tracking-widest font-black opacity-40 mr-1">Filtrar por:</span>

                <!-- Todas las activas -->
                <button
                    class="badge badge-lg cursor-pointer font-bold transition-all gap-1
                        {activeFilter === 'active' ? 'badge-primary' : 'badge-ghost border border-base-300 hover:border-primary'}"
                    onclick={() => activeFilter = 'active'}
                >
                    Todas las activas ({activeOrders.length})
                </button>

                <!-- Pendientes -->
                <button
                    class="badge badge-lg cursor-pointer font-bold transition-all
                        {activeFilter === 'PENDING' ? 'badge-warning' : 'badge-ghost border border-base-300 hover:border-warning'}"
                    onclick={() => activeFilter = 'PENDING'}
                >
                    ⏳ Pendiente ({pendingOrders.length})
                </button>

                <!-- Preparando -->
                <button
                    class="badge badge-lg cursor-pointer font-bold transition-all
                        {activeFilter === 'PREPARING' ? 'badge-primary' : 'badge-ghost border border-base-300 hover:border-primary'}"
                    onclick={() => activeFilter = 'PREPARING'}
                >
                    🍳 Preparando ({preparingOrders.length})
                </button>

                <!-- Listos -->
                <button
                    class="badge badge-lg cursor-pointer font-bold transition-all
                        {activeFilter === 'READY' ? 'badge-success' : 'badge-ghost border border-base-300 hover:border-success'}"
                    onclick={() => activeFilter = 'READY'}
                >
                    ✅ Listos ({readyOrders.length})
                </button>
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
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {#each filteredOrders as order (order.id)}
                {@const progress = getOrderProgress(order)}
                {@const isFinished = order.status === 'PAID' || order.status === 'DELIVERED' || order.status === 'CANCELLED'}

                {@const glow = order.status === 'PENDING' ? 'shadow-[0_0_25px_var(--tw-shadow-color)] shadow-warning/40 border-warning/30' : order.status === 'PREPARING' ? 'shadow-[0_0_25px_var(--tw-shadow-color)] shadow-primary/40 border-primary/30' : order.status === 'READY' ? 'shadow-[0_0_25px_var(--tw-shadow-color)] shadow-success/40 border-success/30' : order.status === 'CANCELLED' ? 'shadow-[0_0_25px_var(--tw-shadow-color)] shadow-error/40 border-error/30' : 'shadow-sm border-base-content/5'}
                <div class="card bg-base-100/60 backdrop-blur-xl hover:-translate-y-1 transition-all duration-300 flex flex-col rounded-3xl border relative overflow-hidden group {glow}">
                    <div class="absolute inset-0 bg-gradient-to-br from-base-content/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                    <div class="card-body p-6 flex flex-col gap-0 z-10">

                        <!-- ── Cabecera de la tarjeta ──────────────────────── -->
                        <div class="flex justify-between items-start mb-3">
                            <div class="flex flex-col gap-1">
                                <span class="text-xs font-black uppercase tracking-widest opacity-50 px-2 py-1 bg-base-200 rounded w-fit">
                                    #{order.id}
                                </span>
                                {#if order.is_paid}
                                    <span class="badge badge-success badge-xs font-black text-[9px] border-none">PAGADO</span>
                                {/if}
                            </div>
                            <div class="flex flex-col items-end gap-1">
                                <span class="badge badge-sm font-bold {getStatusBadgeClass(order.status)}">
                                    {orderStatusLabel[order.status] ?? order.status}
                                </span>
                                <span class="text-[10px] opacity-50 font-semibold">{getTimeAgo(order.created_at)}</span>
                            </div>
                        </div>

                        <h3 class="text-xl font-bold leading-tight">
                            {order.table_id ? `Mesa ${order.table_id}` : 'Mostrador'}
                        </h3>
                        <p class="text-xs opacity-60 uppercase font-black tracking-tight mt-0.5 mb-4">
                            {order.type === 'DINE_IN' ? 'Comedor' : 'Para Llevar'} • {new Date(order.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                        </p>

                        <!-- ── Progreso global ─────────────────────────────── -->
                        {#if !isFinished && (order.items ?? []).length > 0}
                            <div class="mb-3">
                                <div class="flex justify-between text-[10px] font-bold opacity-60 mb-1 uppercase tracking-wider">
                                    <span>Progreso</span>
                                    <span>{progress}%</span>
                                </div>
                                <div class="w-full h-1.5 bg-base-200 rounded-full overflow-hidden">
                                    <div
                                        class="h-full rounded-full transition-all duration-500 {progress === 100 ? 'bg-success' : 'bg-primary'}"
                                        style="width: {progress}%"
                                    ></div>
                                </div>
                            </div>
                        {/if}

                        <!-- ── Lista de ítems con estado ───────────────────── -->
                        {#if order.items && order.items.length > 0}
                            <div class="flex flex-col gap-1.5 mb-4 flex-grow">
                                {#each order.items as item}
                                    {@const cfg = itemStatusConfig[item.status ?? 'PENDING'] ?? itemStatusConfig['PENDING']}
                                    <div class="flex items-start gap-2 p-2 rounded-lg {
                                        item.status === 'CANCELLED' ? 'opacity-40 bg-error/5' :
                                        item.status === 'READY'     ? 'bg-success/10' :
                                        item.status === 'PREPARING' ? 'bg-primary/5' :
                                        'bg-base-200/40'
                                    }">
                                        <!-- Indicador de color -->
                                        <div class="mt-1.5 w-2 h-2 rounded-full shrink-0 {cfg.dotCls}"></div>

                                        <!-- Nombre + modificadores -->
                                        <div class="flex-1 min-w-0">
                                            <span class="text-sm font-bold leading-tight {item.status === 'CANCELLED' ? 'line-through' : ''}">
                                                {item.quantity}× {item.product?.name ?? 'Producto'}
                                            </span>
                                            {#if item.modifiers && item.modifiers.length > 0}
                                                <div class="flex flex-wrap gap-1 mt-0.5">
                                                    {#each item.modifiers as mod}
                                                        <span class="text-[9px] opacity-60 bg-base-300 px-1.5 py-0.5 rounded">+ {mod.name}</span>
                                                    {/each}
                                                </div>
                                            {/if}
                                        </div>

                                        <!-- Estado + botón de avance (solo si tiene permiso) -->
                                        <div class="flex items-center gap-1 shrink-0">
                                            <span class="text-[10px] font-black uppercase tracking-tight {cfg.cls}">
                                                {cfg.label}
                                            </span>
                                            {#if can.manageKitchenStatus() && !isFinished && (item.status === 'PENDING' || item.status === 'PREPARING')}
                                                <button
                                                    class="btn btn-xs rounded-full px-2 h-5 min-h-0 leading-none
                                                        {item.status === 'PENDING' ? 'btn-warning btn-outline' : 'btn-primary'}"
                                                    onclick={() => handleItemAdvance(order, item)}
                                                    title={item.status === 'PENDING' ? 'Empezar preparación' : 'Marcar como listo'}
                                                    id="advance-item-{item.id}"
                                                >
                                                    {item.status === 'PENDING' ? '▶' : '✓'}
                                                </button>
                                            {/if}
                                        </div>
                                    </div>
                                {/each}
                            </div>
                        {:else}
                            <div class="flex-grow py-3 text-center opacity-30 text-xs italic">— sin artículos —</div>
                        {/if}

                        <!-- ── Total + acciones ────────────────────────────── -->
                        <div class="pt-3 border-t border-base-200 flex justify-between items-center gap-2 mt-auto">
                            <span class="font-mono text-lg font-black text-primary">
                                ${calculateTotal(order).toFixed(2)}
                            </span>
                            <div class="flex gap-1 items-center flex-wrap justify-end">
                                <!-- Cobrar y/o Entregar (solo si tiene permiso can_charge) -->
                                {#if can.charge()}
                                    {#if order.status === 'READY' && order.is_paid}
                                        <button
                                            class="btn btn-success btn-sm font-bold shadow-sm"
                                            onclick={() => handleComplete(order.id)}
                                            id="deliver-order-{order.id}"
                                        >
                                            Entregar
                                        </button>
                                    {:else if order.status === 'READY' && !order.is_paid}
                                        <button
                                            onclick={() => openCartForCharge(order)}
                                            class="btn btn-primary btn-sm font-bold shadow-sm"
                                            id="charge-order-{order.id}"
                                        >
                                            Cobrar y Entregar
                                        </button>
                                    {:else if order.status !== 'PAID' && order.status !== 'DELIVERED' && order.status !== 'CANCELLED' && !order.is_paid}
                                        <button
                                            onclick={() => openCartForCharge(order)}
                                            class="btn btn-outline btn-primary btn-sm font-bold shadow-sm"
                                            id="charge-order-{order.id}"
                                        >
                                            Cobrar
                                        </button>
                                    {/if}
                                {/if}

                                <!-- Imprimir ticket -->
                                <button
                                    class="btn btn-ghost btn-sm btn-square"
                                    onclick={() => handlePrintTicket(order.id)}
                                    disabled={printingOrderId === order.id}
                                    title="Imprimir Ticket"
                                    id="print-ticket-{order.id}"
                                    aria-label="Imprimir ticket de la orden {order.id}"
                                >
                                    {#if printingOrderId === order.id}
                                        <span class="loading loading-spinner loading-xs"></span>
                                    {:else}
                                        🖨️
                                    {/if}
                                </button>

                                <!-- Cancelar / eliminar -->
                                {#if order.status !== 'PAID' && order.status !== 'DELIVERED' && order.status !== 'CANCELLED'}
                                    <button
                                        class="btn btn-ghost btn-sm btn-square text-error"
                                        onclick={() => handleCancelOrDelete(order)}
                                        title={order.items && order.items.length > 0 ? "Cancelar Pedido" : "Eliminar Pedido Vacío"}
                                        id="cancel-order-{order.id}"
                                        aria-label="Cancelar orden {order.id}"
                                    >
                                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                        </svg>
                                    </button>
                                {/if}
                            </div>
                        </div>
                    </div>
                </div>
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
            <button class="btn border border-base-300 btn-ghost text-base-content/70" onclick={() => cancellingOrder = null} disabled={isCancelling}>
                Volver
            </button>
            <button class="btn btn-error text-white shadow-xl" onclick={confirmCancel} disabled={!cancelReason.trim() || isCancelling}>
                {#if isCancelling}
                    <span class="loading loading-spinner"></span>
                {:else}
                    Confirmar Cancelación
                {/if}
            </button>
        </div>
    </div>
</div>
{/if}
