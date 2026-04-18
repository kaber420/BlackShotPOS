<script lang="ts">
    import { onMount, onDestroy } from 'svelte';
    import { OrderService, OrderStatus } from '$lib/api/orders';
    import { TableService, type Table } from '$lib/api/tables';
    import { marked } from 'marked';
    import {
        printComanda,
        getAvailableMethods,
        getRecommendedMethod,
        type PrintMethod,
        type PrintMethodInfo,
    } from '$lib/printer';
    import Button from '$lib/components/ui/Button.svelte';
    import OrderCard from '$lib/components/OrderCard.svelte';
    import { posSocket } from '$lib/pos_socket.svelte';

    // ── Estado de la aplicación ──────────────────────────────────────────────
    let orders = $derived<any[]>(posSocket.kitchenOrders);
    let tables = $state<Table[]>([]);
    let isLoading = $state(true);

    // ── Estado de impresión ──────────────────────────────────────────────────
    let printMethods = $state<PrintMethodInfo[]>([]);
    let selectedMethod = $state<PrintMethod>('download');
    let printingOrderId = $state<number | null>(null);
    let showMethodPicker = $state(false);
    let printError = $state<string | null>(null);

    // ── Modal de receta ────────────────────────────────────────────────
    let recipeModal = $state<{ name: string; markdown: string } | null>(null);

    // ── WebSocket Connection ─────────────────────────────────────────────────
    onMount(() => {
        // Cargar mesas y configurar impresión (no bloquean el KDS)
        TableService.getAll().then(t => (tables = t)).catch(console.error);

        printMethods = getAvailableMethods();
        selectedMethod = getRecommendedMethod();

        posSocket.subscribe("kitchen_orders");
        // Si ya tenemos data, no hay necesidad de esperar
        if (posSocket.kitchenOrders.length > 0) {
            isLoading = false;
        } else {
            setTimeout(() => isLoading = false, 300);
        }

        return () => {
            posSocket.unsubscribe("kitchen_orders");
        };
    });

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

<div class="p-6 md:p-8 lg:p-10 flex flex-col gap-8 w-full flex-1 min-h-0 overflow-y-auto">
    <!-- ── Header ──────────────────────────────────────────────────────────── -->
    <header class="flex flex-col gap-3">
        <div class="flex justify-between items-center flex-wrap gap-4">
            <div>
                <h1 class="text-4xl font-extrabold tracking-tight">Cocina (KDS)</h1>
                <p class="text-lg opacity-70">Control de comandas y tiempos de preparación.</p>
            </div>

            <div class="flex items-center gap-3 flex-wrap">
                <!-- Badge de conexión -->
                <div class="badge {statusColors[posSocket.status]} gap-2 p-4 font-bold">
                    {#if posSocket.status === 'open'}
                        <span class="relative flex h-2 w-2">
                            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75"></span>
                            <span class="relative inline-flex rounded-full h-2 w-2 bg-success"></span>
                        </span>
                    {/if}
                    {statusLabels[posSocket.status]}
                </div>

                <!-- Selector de método de impresión -->
                <div class="relative">
                    <Button
                        variant="outline"
                        size="sm"
                        onclick={() => (showMethodPicker = !showMethodPicker)}
                        title="Cambiar método de impresión"
                        id="print-method-btn"
                    >
                        <span class="flex items-center gap-2">
                            🖨️
                            {printMethods.find(m => m.id === selectedMethod)?.label ?? 'Impresión'}
                            <svg class="h-3 w-3 opacity-60" viewBox="0 0 20 20" fill="currentColor">
                                <path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clip-rule="evenodd" />
                            </svg>
                        </span>
                    </Button>

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
                <Button
                    variant="ghost"
                    circle
                    size="sm"
                    onclick={() => posSocket.connect()}
                    aria-label="Reconectar WebSocket"
                    title="Reconectar"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                </Button>
            </div>
        </div>

        <!-- Error de impresión -->
        {#if printError}
            <div class="alert alert-error">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>Error de impresión: {printError}</span>
                <Button variant="ghost" size="sm" onclick={() => (printError = null)}>✕</Button>
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
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-6">
            {#each orders as order (order.id)}
                <OrderCard
                    {order}
                    view="kitchen"
                    {printingOrderId}
                    onItemComplete={handleItemComplete}
                    onItemCancel={handleItemCancel}
                    onViewRecipe={(name, markdown) => recipeModal = { name, markdown }}
                    onCompleteOrder={handleComplete}
                    onCancelOrder={handleCancel}
                    onPrint={handlePrintComanda}
                />
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

<!-- ── Modal de Receta ──────────────────────────────────────────── -->
{#if recipeModal}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div class="modal modal-open z-50" onclick={() => recipeModal = null}>
        <div
            class="modal-box max-w-2xl max-h-[80vh] overflow-y-auto"
            onclick={(e) => e.stopPropagation()}
        >
            <div class="flex items-center justify-between mb-4 pb-3 border-b border-base-200">
                <h3 class="text-xl font-black flex items-center gap-2">
                    📖 {recipeModal.name}
                </h3>
                <Button
                    variant="ghost"
                    size="sm"
                    circle
                    onclick={() => recipeModal = null}
                    aria-label="Cerrar receta"
                >
                    ✕
                </Button>
            </div>
            <!-- Contenido Markdown renderizado -->
            <div class="prose prose-sm max-w-none">
                {@html marked(recipeModal.markdown)}
            </div>
        </div>
    </div>
{/if}
