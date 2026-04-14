<script lang="ts">
    import { onMount, onDestroy } from 'svelte';
    import { OrderService, OrderStatus } from '$lib/api/orders';
    import { TableService, type Table } from '$lib/api/tables';
    import {
        printComanda,
        getAvailableMethods,
        getRecommendedMethod,
        type PrintMethod,
        type PrintMethodInfo,
    } from '$lib/printer';

    // ── Estado de la aplicación ──────────────────────────────────────────────
    let orders = $state<any[]>([]);
    let tables = $state<Table[]>([]);
    let isLoading = $state(true);
    let connectionStatus = $state<'connecting' | 'open' | 'closed'>('connecting');

    // ── Estado de impresión ──────────────────────────────────────────────────
    let printMethods = $state<PrintMethodInfo[]>([]);
    let selectedMethod = $state<PrintMethod>('download');
    let printingOrderId = $state<number | null>(null);
    let showMethodPicker = $state(false);
    let printError = $state<string | null>(null);

    // ── WebSocket Connection ─────────────────────────────────────────────────
    let socket: WebSocket | null = null;
    let isDestroyed = false;

    onMount(() => {
        // Cargar mesas y configurar impresión (no bloquean el KDS)
        TableService.getAll().then(t => (tables = t)).catch(console.error);

        printMethods = getAvailableMethods();
        selectedMethod = getRecommendedMethod();

        connectWebSocket();
        return () => {
            isDestroyed = true;
            if (socket) socket.close();
        };
    });

    function connectWebSocket() {
        if (typeof window === 'undefined' || isDestroyed) return;

        const token = localStorage.getItem('X-Omni-Token');
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        // Importante: la ruta debe coincidir con el backend
        const url = `${protocol}//${host}/api/v1/pos/ws/pos?token=${encodeURIComponent(token || '')}`;

        console.log("🔌 Conectando a WebSocket cocina...");
        connectionStatus = 'connecting';
        socket = new WebSocket(url);

        socket.onopen = () => {
            console.log("🔌 WebSocket Cocina conectado");
            connectionStatus = 'open';
            socket?.send(JSON.stringify({ action: "subscribe", topic: "kitchen_orders" }));
            isLoading = false;
        };

        socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.error) {
                    console.error("Error desde el servidor:", data.detail);
                } else {
                    orders = data;
                    isLoading = false;
                }
            } catch (e) {
                console.error("Error parseando datos WebSocket", e);
            }
        };

        socket.onclose = () => {
            if (isDestroyed) return;
            console.log("🔌 WebSocket Cocina desconectado");
            connectionStatus = 'closed';
            // Reintentar en 3 segundos
            setTimeout(connectWebSocket, 3000);
        };

        socket.onerror = (err) => {
            console.error("❌ Error en WebSocket:", err);
            connectionStatus = 'closed';
        };
    }

    // ── Acciones de orden ────────────────────────────────────────────────────
    async function handleItemComplete(order: any, item: any) {
        try {
            if (item.status === OrderStatus.PENDING) {
                await OrderService.updateItemStatus(order.id, item.id, OrderStatus.PREPARING);
            } else if (item.status === OrderStatus.PREPARING) {
                await OrderService.updateItemStatus(order.id, item.id, OrderStatus.READY);
            }
            // La actualización llegará por WebSocket automáticamente
        } catch (e) {
            alert(`Error al actualizar platillo: ${e}`);
        }
    }

    async function handleItemCancel(order: any, item: any) {
        if (!confirm(`¿Estás seguro de que deseas ANULAR este platillo?`)) return;
        
        try {
            await OrderService.updateItemStatus(order.id, item.id, OrderStatus.CANCELLED);
            // La actualización llegará por WebSocket automáticamente
        } catch (e) {
            alert(`Error al anular platillo: ${e}`);
        }
    }

    async function handleComplete(order: any) {
        try {
            if (order.status === OrderStatus.PENDING) {
                await OrderService.updateStatus(order.id, OrderStatus.PREPARING);
            } else if (order.status === OrderStatus.PREPARING) {
                await OrderService.updateStatus(order.id, OrderStatus.READY);
            }
        } catch (e) {
            alert(`Error al completar orden completa: ${e}`);
        }
    }

    async function handleCancel(order: any) {
        if (!confirm(`¿Estás seguro de que deseas ANULAR la Orden #${order.id} completa?`)) return;
        
        try {
            await OrderService.updateStatus(order.id, OrderStatus.CANCELLED);
        } catch (e) {
            alert(`Error al anular orden: ${e}`);
        }
    }
    // ── Acciones de impresión ─────────────────────────────────────────────────
    async function handlePrintComanda(orderId: number) {
        printError = null;
        printingOrderId = orderId;
        try {
            await printComanda(orderId, selectedMethod);
        } catch (e: any) {
            printError = e?.message ?? 'Error al imprimir';
        } finally {
            printingOrderId = null;
        }
    }

    function togglePreferredMethod(methodId: PrintMethod) {
        import('$lib/printer').then(m => {
            m.savePreferredMethod(methodId);
            selectedMethod = methodId;
            showMethodPicker = false;
        });
    }

    // ── Helpers de UI ─────────────────────────────────────────────────────────
    function getTableNumber(tableId?: number) {
        if (!tableId) return 'MOSTRADOR';
        const table = tables.find(t => t.id === tableId);
        return table ? `MESA ${table.number}` : `ID: ${tableId}`;
    }

    function getTimeAgo(dateStr: string) {
        const diffMins = Math.floor((Date.now() - new Date(dateStr).getTime()) / 60000);
        return diffMins < 1 ? 'ahora' : `${diffMins} min`;
    }

    const statusColors: Record<string, string> = {
        connecting: 'badge-warning',
        open: 'badge-success',
        closed: 'badge-error',
    };
    const statusLabels: Record<string, string> = {
        connecting: 'CONECTANDO',
        open: 'EN VIVO',
        closed: 'DESCONECTADO',
    };
</script>

<div class="p-6 md:p-8 lg:p-12 max-w-7xl mx-auto flex flex-col gap-8">
    <!-- ── Header ──────────────────────────────────────────────────────────── -->
    <header class="flex flex-col gap-3">
        <div class="flex justify-between items-center flex-wrap gap-4">
            <div>
                <h1 class="text-4xl font-extrabold tracking-tight">Cocina (KDS)</h1>
                <p class="text-lg opacity-70">Control de comandas y tiempos de preparación.</p>
            </div>

            <div class="flex items-center gap-3 flex-wrap">
                <!-- Badge de conexión -->
                <div class="badge {statusColors[connectionStatus]} gap-2 p-4 font-bold">
                    {#if connectionStatus === 'open'}
                        <span class="relative flex h-2 w-2">
                            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75"></span>
                            <span class="relative inline-flex rounded-full h-2 w-2 bg-success"></span>
                        </span>
                    {/if}
                    {statusLabels[connectionStatus]}
                </div>

                <!-- Selector de método de impresión -->
                <div class="relative">
                    <button
                        class="btn btn-outline btn-sm gap-2"
                        onclick={() => (showMethodPicker = !showMethodPicker)}
                        title="Cambiar método de impresión"
                        id="print-method-btn"
                    >
                        🖨️
                        {printMethods.find(m => m.id === selectedMethod)?.label ?? 'Impresión'}
                        <svg class="h-3 w-3 opacity-60" viewBox="0 0 20 20" fill="currentColor">
                            <path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clip-rule="evenodd" />
                        </svg>
                    </button>

                    {#if showMethodPicker}
                        <div
                            class="absolute right-0 top-full mt-2 z-50 card bg-base-200 shadow-2xl border border-base-300 w-72"
                            onclick={(e) => e.stopPropagation()}
                            onkeydown={(e) => e.stopPropagation()}
                            role="dialog"
                            aria-label="Selector de método de impresión"
                            tabindex="-1"
                        >
                            <div class="card-body p-4 gap-3">
                                <h3 class="font-bold text-sm uppercase tracking-wider opacity-60">Método de impresión</h3>
                                {#each printMethods as method}
                                    <div
                                        class="flex items-start gap-3 p-3 rounded-xl text-left transition-colors group cursor-pointer
                                            {selectedMethod === method.id ? 'bg-primary/20 border border-primary/40' : 'hover:bg-base-300'}
                                            {!method.available ? 'opacity-30 cursor-not-allowed' : ''}"
                                        role="button"
                                        tabindex="0"
                                        onclick={() => { if(method.available) { selectedMethod = method.id; showMethodPicker = false; } }}
                                        onkeydown={(e) => { if (e.key === 'Enter' && method.available) { selectedMethod = method.id; showMethodPicker = false; } }}
                                        id="print-method-{method.id}"
                                    >
                                        <span class="text-xl">{method.icon}</span>
                                        <div class="flex-1">
                                            <p class="font-semibold text-sm">{method.label}</p>
                                            <p class="text-xs opacity-60">{method.description}</p>
                                            
                                            {#if selectedMethod === method.id}
                                                <p class="text-[10px] text-primary font-bold mt-1 uppercase tracking-tighter">Seleccionado</p>
                                            {:else if method.available}
                                                <button 
                                                    class="text-[10px] text-accent font-bold mt-1 uppercase tracking-tighter hover:underline hidden group-hover:block"
                                                    onclick={(e) => { e.stopPropagation(); togglePreferredMethod(method.id); }}
                                                >
                                                    Fijar como favorito
                                                </button>
                                            {/if}
                                        </div>
                                    </div>
                                {/each}
                            </div>
                        </div>
                    {/if}
                </div>

                <!-- Botón reconexión manual -->
                <button
                    class="btn btn-ghost btn-circle btn-sm"
                    onclick={() => { socket?.close(); connectWebSocket(); }}
                    aria-label="Reconectar WebSocket"
                    title="Reconectar"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                </button>
            </div>
        </div>

        <!-- Error de impresión -->
        {#if printError}
            <div class="alert alert-error">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>Error de impresión: {printError}</span>
                <button class="btn btn-ghost btn-sm" onclick={() => (printError = null)}>✕</button>
            </div>
        {/if}
    </header>

    <!-- ── Contenido principal ─────────────────────────────────────────────── -->
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
            {#each orders as order (order.id)}
                <div class="card bg-base-100 shadow-xl border-l-4 {order.status === 'PENDING' ? 'border-warning' : 'border-primary'} flex flex-col">
                    <div class="card-body p-6 flex flex-col h-full">
                        <!-- Cabecera de la comanda -->
                        <div class="flex justify-between items-start mb-4">
                            <div>
                                <h2 class="card-title text-2xl font-bold">Orden #{order.id}</h2>
                                <p class="text-xs font-bold uppercase tracking-widest opacity-60">
                                    {getTableNumber(order.table_id)} • {getTimeAgo(order.created_at)}
                                </p>
                            </div>
                            <div class="flex flex-col items-end gap-1">
                                <div class="badge {order.status === 'PENDING' ? 'badge-warning' : 'badge-primary'} font-bold p-3">
                                    {order.status === 'PENDING' ? 'PENDIENTE' : 'PREPARANDO'}
                                </div>
                                {#if order.is_paid}
                                    <div class="badge badge-success badge-sm font-black text-[10px] py-1 px-2 border-none">PAGADO</div>
                                {/if}
                            </div>
                        </div>

                        <!-- Items -->
                        <div class="space-y-3 mb-6 flex-grow">
                            {#if order.items}
                                {#each order.items as item}
                                    <div class="flex flex-col bg-base-200/50 p-3 rounded-lg border 
                                        {item.status === 'CANCELLED' ? 'border-error/50 opacity-50 grayscale' : 
                                         item.status === 'READY' ? 'border-success/50 opacity-50 bg-success/10' : 
                                         'border-base-300/50'}">
                                        
                                        <div class="flex justify-between items-start gap-2">
                                            <div class="flex flex-col">
                                                <span class="font-bold text-lg {item.status === 'CANCELLED' ? 'line-through' : ''}">
                                                    {item.quantity}x {item.product?.name ?? 'Producto'}
                                                </span>
                                                {#if item.status === 'CANCELLED'}
                                                    <span class="text-error text-xs font-bold">ANULADO</span>
                                                {:else if item.status === 'READY'}
                                                    <span class="text-success text-xs font-bold">LISTO</span>
                                                {:else if item.status === 'PREPARANDO'}
                                                    <span class="text-primary text-xs font-bold animated-pulse">EN PREPARACIÓN</span>
                                                {/if}
                                            </div>
                                            <div class="flex gap-2 min-w-max">
                                                {#if item.status === 'PENDING'}
                                                    <button class="btn btn-error btn-outline btn-sm btn-square" onclick={() => handleItemCancel(order, item)} title="Anular platillo">🗑️</button>
                                                    <button class="btn btn-primary btn-outline btn-sm" onclick={() => handleItemComplete(order, item)}>Empezar</button>
                                                {:else if item.status === 'PREPARANDO'}
                                                    <button class="btn btn-primary btn-sm" onclick={() => handleItemComplete(order, item)}>✓ Listo</button>
                                                {/if}
                                            </div>
                                        </div>

                                        <div class="flex justify-between items-center mt-1">
                                            {#if item.variant}
                                                <span class="badge badge-outline badge-sm">{item.variant.measure.name}</span>
                                            {/if}
                                        </div>

                                        {#if item.modifiers && item.modifiers.length > 0}
                                            <div class="flex flex-wrap gap-1 mt-1">
                                                {#each item.modifiers as mod}
                                                    <span class="badge badge-sm badge-outline opacity-70">+ {mod.name}</span>
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

                        <!-- Acciones globales de la orden -->
                        <div class="card-actions flex gap-2 mt-auto pt-4 border-t border-base-200">
                            <!-- Botón de anulación -->
                            {#if order.status === 'PENDING'}
                                <button
                                    class="btn btn-outline btn-error btn-square"
                                    onclick={() => handleCancel(order)}
                                    title="Anular toda la orden"
                                    id="cancel-order-{order.id}"
                                    aria-label="Anular la orden completa {order.id}"
                                >
                                    🗑️
                                </button>
                            {/if}

                            <!-- Botón de impresión -->
                            <button
                                class="btn btn-outline btn-square"
                                onclick={() => handlePrintComanda(order.id)}
                                disabled={printingOrderId === order.id}
                                title="Imprimir comanda ({printMethods.find(m=>m.id===selectedMethod)?.label})"
                                id="print-comanda-{order.id}"
                                aria-label="Imprimir comanda de la orden {order.id}"
                            >
                                {#if printingOrderId === order.id}
                                    <span class="loading loading-spinner loading-sm"></span>
                                {:else}
                                    🖨️
                                {/if}
                            </button>

                            <!-- Botón completar toda la orden -->
                            <button
                                class="btn {order.status === 'PENDING' ? 'btn-outline border-primary' : 'btn-primary'} flex-1 text-lg"
                                onclick={() => handleComplete(order)}
                                id="complete-order-{order.id}"
                            >
                                {order.status === 'PENDING' ? 'Empezar Toda la Orden' : '✓ Orden Lista'}
                            </button>
                        </div>
                    </div>
                </div>
            {/each}
        </div>
    {/if}
</div>

<!-- Cerrar el picker al hacer click fuera -->
{#if showMethodPicker}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div
        class="fixed inset-0 z-40"
        onclick={() => (showMethodPicker = false)}
    ></div>
{/if}
