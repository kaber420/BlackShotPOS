<script lang="ts">
    import { onMount, onDestroy } from 'svelte';
    import { OrderService, OrderStatus } from '$lib/api/orders';
    import { KitchenService } from '$lib/api/kitchen';
    import { TableService, type Table } from '$lib/api/tables';
    import { ProductionAreaService, type ProductionArea } from '$lib/api/production_areas';
    import { appState } from '$lib/app_state.svelte';
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

    // ── Estado de Áreas de Producción ─────────────────────────────────────────
    let productionAreas = $state<ProductionArea[]>([]);
    let selectedAreaId = $state<number | null>(null);

    // Cargar áreas
    async function loadAreas() {
        try {
            productionAreas = await ProductionAreaService.getAll();
        } catch (e) {
            console.error("Error cargando áreas:", e);
        }
    }

    // Persistencia del área seleccionada
    onMount(() => {
        const saved = localStorage.getItem('bs_kds_area_id');
        if (saved && saved !== "null") selectedAreaId = parseInt(saved);
    });

    $effect(() => {
        if (selectedAreaId !== null) {
            localStorage.setItem('bs_kds_area_id', selectedAreaId.toString());
        } else {
            localStorage.setItem('bs_kds_area_id', "null");
        }
    });

    // ── Filtrado de Órdenes e Ítems ──────────────────────────────────────────
    let filteredOrders = $derived.by(() => {
        if (selectedAreaId === null) return orders;

        return orders
            .map(order => {
                // Filtrar items que pertenecen al área seleccionada
                const itemsForArea = (order.items || []).filter(item => item.production_area_id === selectedAreaId);
                if (itemsForArea.length === 0) return null;
                
                // Retornar una copia de la orden solo con los items de esa área
                return { ...order, items: itemsForArea };
            })
            .filter(o => o !== null) as any[];
    });

    // ── Estado de impresión ──────────────────────────────────────────────────
    let printingOrderId = $state<number | null>(null);

    // ── Modal de receta ────────────────────────────────────────────────
    let recipeModal = $state<{ orderId: number; itemId: number; name: string; markdown: string } | null>(null);
    let recipeStates = $state<Record<string, Record<number, boolean>>>({});
    let timerStates = $state<Record<string, Record<number, { seconds: number; total: number; running: boolean; finished: boolean }>>>({});

    function getRecipeKey(orderId: number, itemId: number) {
        return `${orderId}-${itemId}`;
    }

    // Intervalo global para cronómetros
    onMount(() => {
        const interval = setInterval(() => {
            for (const key in timerStates) {
                for (const tIdx in timerStates[key]) {
                    const timer = timerStates[key][tIdx];
                    if (timer.running && timer.seconds > 0) {
                        timer.seconds--;
                        if (timer.seconds === 0) {
                            timer.running = false;
                            timer.finished = true;
                            // Opcional: Sonido de alerta
                        }
                    }
                }
            }
        }, 1000);
        return () => clearInterval(interval);
    });

    function toggleTimer(orderId: number, itemId: number, tIdx: number, durationMins: number) {
        const key = getRecipeKey(orderId, itemId);
        if (!timerStates[key]) timerStates[key] = {};
        if (!timerStates[key][tIdx]) {
            timerStates[key][tIdx] = { 
                seconds: durationMins * 60, 
                total: durationMins * 60, 
                running: true, 
                finished: false 
            };
        } else {
            const timer = timerStates[key][tIdx];
            if (timer.finished) {
                // Reset
                timer.seconds = timer.total;
                timer.finished = false;
                timer.running = true;
            } else {
                timer.running = !timer.running;
            }
        }
    }

    function formatTime(seconds: number) {
        const m = Math.floor(seconds / 60);
        const s = seconds % 60;
        return `${m}:${s.toString().padStart(2, '0')}`;
    }

    let renderedRecipe = $derived.by(() => {
        if (!recipeModal) return '';
        let cbIdx = 0;
        let tIdx = 0;
        const key = getRecipeKey(recipeModal.orderId, recipeModal.itemId);
        
        // 1. Procesar Checkboxes
        let html = marked(recipeModal.markdown).replace(/<input disabled="" type="checkbox">/g, () => {
            const current = cbIdx++;
            const isChecked = recipeStates[key]?.[current] ? 'checked' : '';
            return `<input type="checkbox" data-cb-idx="${current}" ${isChecked} class="checkbox checkbox-primary checkbox-sm mr-2">`;
        });

        // 2. Procesar Timers {timer:5}
        html = html.replace(/\{timer:(\d+)\}/g, (_, mins) => {
            const current = tIdx++;
            const timer = timerStates[key]?.[current];
            const duration = parseInt(mins);
            
            let label = `${duration} min`;
            let cls = "btn-outline border-primary/30";
            
            if (timer) {
                label = formatTime(timer.seconds);
                if (timer.finished) {
                    cls = "btn-error animate-bounce shadow-lg shadow-error/50 text-white";
                    label = "¡LISTO! 🔔";
                } else if (timer.running) {
                    cls = "btn-primary shadow-lg shadow-primary/30 text-white";
                }
            }

            return `<button class="btn btn-xs ${cls} mx-1 font-mono tracking-tighter" data-t-idx="${current}" data-duration="${duration}">⏱️ ${label}</button>`;
        });

        return html;
    });

    function toggleRecipeStep(orderId: number, itemId: number, stepIndex: number) {
        const key = getRecipeKey(orderId, itemId);
        if (!recipeStates[key]) recipeStates[key] = {};
        recipeStates[key][stepIndex] = !recipeStates[key][stepIndex];
    }

    // ── WebSocket Connection ─────────────────────────────────────────────────
    onMount(async () => {
        loadAreas();
        TableService.getAll().then(t => (tables = t)).catch(console.error);

        posSocket.subscribe("kitchen_orders");
        
        // Si no tenemos datos, forzamos una carga inicial via REST
        if (posSocket.kitchenOrders.length === 0) {
            isLoading = true;
            try {
                // En realidad esperamos al socket, pero isLoading da feedback visual
            } catch (e) {
                console.error("Error en carga inicial KDS:", e);
            } finally {
                // No quitamos isLoading hasta que el socket responda o pase un timeout
                setTimeout(() => (isLoading = false), 1000);
            }
        } else {
            isLoading = false;
        }

        return () => {
            posSocket.unsubscribe("kitchen_orders");
        };
    });

    // ── Acciones de orden ────────────────────────────────────────────────────
    async function handleItemComplete(order: any, item: any) {
        if (!item.kitchen_ticket_id) {
            alert("Error: Este platillo no tiene un ticket de cocina vinculado.");
            return;
        }

        try {
            if (item.status === OrderStatus.PENDING) {
                await KitchenService.startPreparing(
                    item.kitchen_ticket_id, 
                    appState.userUuid || "system", 
                    appState.userName || "KDS"
                );
            } else if (item.status === OrderStatus.PREPARING) {
                await KitchenService.markAsReady(item.kitchen_ticket_id);
            }
            // La actualización llegará por WebSocket automáticamente
        } catch (e: any) {
            alert(`Error al actualizar platillo: ${e.message || e}`);
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
        // En un sistema desacoplado, "Completar Orden" en KDS significa marcar todos sus tickets como LISTOS.
        const pendingItems = (order.items || []).filter((i: any) => 
            i.status === OrderStatus.PENDING || i.status === OrderStatus.PREPARING
        );

        if (pendingItems.length === 0) return;

        try {
            const promises = pendingItems.map(async (item: any) => {
                if (!item.kitchen_ticket_id) return;
                
                // Si está pendiente, primero marcar como preparando (para auditoría) y luego listo, 
                // o simplemente listo (el backend de kitchen lo permite).
                return KitchenService.markAsReady(item.kitchen_ticket_id);
            });
            await Promise.all(promises);
        } catch (e: any) {
            alert(`Error al completar orden completa: ${e.message || e}`);
        }
    }

    async function handleCancel(order: any) {
        if (!confirm(`¿Estás seguro de que deseas ANULAR la Orden #${order.id} completa?`)) return;
        
        try {
            await OrderService.updateStatus(order.id, OrderStatus.CANCELLED);
        } catch (e: any) {
            alert(`Error al anular orden: ${e}`);
        }
    }
    // ── Acciones de impresión ─────────────────────────────────────────────────
    async function handlePrintComanda(orderId: number) {
        printingOrderId = orderId;
        try {
            await printComanda(orderId, 'browser');
        } catch (e: any) {
            console.error('Error al imprimir:', e);
        } finally {
            printingOrderId = null;
        }
    }

    // ── Helpers de UI ─────────────────────────────────────────────────────────
    let pendingCount = $derived(filteredOrders.filter(o => o.status === 'PENDING').length);
    let preparingCount = $derived(filteredOrders.filter(o => o.status === 'PREPARING').length);

</script>

<div class="p-6 md:p-8 lg:p-10 flex flex-col gap-8 w-full flex-1 min-h-0 overflow-y-auto">
    <!-- ── Toolbar unificada estilo POS ────────────────────────────────────────── -->
    <div class="flex items-center justify-between bg-base-100 shadow-sm p-2 rounded-xl border border-base-200 shrink-0">
        <div class="flex items-center gap-4 flex-1 px-2">
            <h1 class="text-xl font-black tracking-tight uppercase opacity-80">Cocina (KDS)</h1>
            
            <div class="h-6 w-[1px] bg-base-300 mx-2 hidden md:block"></div>

            <!-- Selector de Área -->
            <div class="flex items-center gap-2">
                <select 
                    bind:value={selectedAreaId}
                    class="select select-bordered select-sm font-bold bg-base-200 border-none focus:ring-0 text-xs uppercase"
                >
                    <option value={null}>🌎 TODAS LAS ÁREAS</option>
                    {#each productionAreas as area}
                        <option value={area.id}>📍 {area.name.toUpperCase()}</option>
                    {/each}
                </select>
            </div>

            <div class="h-6 w-[1px] bg-base-300 mx-2 hidden md:block"></div>

            <!-- Stats Compactas -->
            <div class="flex items-center gap-3">
                <div class="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-warning/10 text-warning border border-warning/20">
                    <span class="text-xs font-black">⏳</span>
                    <span class="text-sm font-black font-mono">{pendingCount}</span>
                    <span class="text-[10px] font-bold uppercase opacity-60 hidden sm:inline">Pendientes</span>
                </div>
                <div class="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-primary/10 text-primary border border-primary/20">
                    <span class="text-xs font-black">🍳</span>
                    <span class="text-sm font-black font-mono">{preparingCount}</span>
                    <span class="text-[10px] font-bold uppercase opacity-60 hidden sm:inline">Preparando</span>
                </div>
            </div>
        </div>

        <div class="flex items-center gap-2">
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

    <!-- ── Contenido principal ─────────────────────────────────────────────── -->
    {#if isLoading}
        <div class="flex justify-center py-20">
            <span class="loading loading-spinner loading-lg text-primary"></span>
        </div>
    {:else if filteredOrders.length === 0}
        <div class="flex flex-col items-center justify-center py-20 bg-base-200 rounded-2xl border-2 border-dashed border-base-300">
            <p class="text-2xl font-bold opacity-20 italic">
                {selectedAreaId ? "No hay comandas para esta área" : "No hay comandas activas"}
            </p>
            <p class="text-sm opacity-10 mt-2">Los pedidos aparecerán aquí automáticamente.</p>
        </div>
    {:else}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-6">
            {#each filteredOrders as order (order.id)}
                <OrderCard
                    {order}
                    view="kitchen"
                    onCompleteOrder={handleComplete}
                    onCancelOrder={handleCancel}
                    onItemComplete={handleItemComplete}
                    onItemCancel={handleItemCancel}
                    onViewRecipe={(orderId, itemId, name, markdown) => recipeModal = { orderId, itemId, name, markdown }}
                    activeRecipes={recipeStates}
                    activeTimers={timerStates}
                    printingOrderId={printingOrderId}
                    onPrint={handlePrintComanda}
                />
            {/each}
        </div>
    {/if}
</div>

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
            <div class="prose prose-sm max-w-none recipe-content" onclick={(e) => {
                const li = e.target.closest('li');
                const btn = e.target.closest('button[data-t-idx]');
                
                if (btn && recipeModal) {
                    const tIdx = parseInt(btn.dataset.tIdx || '0');
                    const duration = parseInt(btn.dataset.duration || '0');
                    toggleTimer(recipeModal.orderId, recipeModal.itemId, tIdx, duration);
                } else if (li && recipeModal) {
                    const checkbox = li.querySelector('input[type="checkbox"]');
                    if (checkbox) {
                        const idx = parseInt(checkbox.dataset.cbIdx || '0');
                        toggleRecipeStep(recipeModal.orderId, recipeModal.itemId, idx);
                    }
                }
            }}>
                {@html renderedRecipe}
            </div>

            <style>
                .recipe-content :global(ul) {
                    list-style-type: none;
                    padding-left: 0;
                }
                .recipe-content :global(li) {
                    display: flex;
                    align-items: center;
                    margin-bottom: 0.5rem;
                    transition: all 0.2s;
                    cursor: pointer;
                    padding: 0.5rem;
                    border-radius: 0.5rem;
                }
                .recipe-content :global(li:hover) {
                    background: rgba(255,255,255,0.05);
                }
                .recipe-content :global(li:has(input:checked)) {
                    text-decoration: line-through;
                    opacity: 0.4;
                    background: rgba(0,255,0,0.05);
                }
                .recipe-content :global(input[type="checkbox"]) {
                    cursor: pointer;
                    pointer-events: auto; /* Asegurar que sea clickable aunque marked lo intente bloquear */
                }
            </style>
        </div>
    </div>
{/if}
