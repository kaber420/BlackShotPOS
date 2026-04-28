<script lang="ts">
    import { OrderStatus } from '$lib/api/orders';
    import type { Order } from '$lib/api/orders';
    import Button from '$lib/components/ui/Button.svelte';
    import { appState } from '$lib/app_state.svelte';

    // ── Props ─────────────────────────────────────────────────────────────
    interface Props {
        order: Order | any;
        view?: 'kitchen' | 'orders';
        canManageKitchenStatus?: boolean; // For 'orders' view
        printingOrderId?: number | null;
        
        // Item Actions
        onItemComplete?: (order: any, item: any) => void;
        onItemCancel?: (order: any, item: any) => void;
        onViewRecipe?: (orderId: number, itemId: number, productName: string, markdown: string) => void;
        activeRecipes?: Record<string, any>;
        activeTimers?: Record<string, any>;
        
        // Global Actions
        onCompleteOrder?: (order: any) => void;
        onCancelOrder?: (order: any) => void;
        onTransferOrder?: (order: any) => void;
        onPrint?: (orderId: number) => void;
        onCharge?: (order: any) => void;
        onDeliver?: (orderId: number) => void;
    }

    let {
        order,
        view = 'orders',
        canManageKitchenStatus = false,
        printingOrderId = null,
        onItemComplete,
        onItemCancel,
        onViewRecipe,
        onCompleteOrder,
        onCancelOrder,
        onTransferOrder,
        onPrint,
        onCharge,
        onDeliver,
        activeRecipes = {},
        activeTimers = {}
    }: Props = $props();

    // ── Helpers ───────────────────────────────────────────────────────────
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
        DELIVERED: { label: 'Entregado ✓',   cls: 'text-fuchsia-400', dotCls: 'bg-fuchsia-400' },
        CANCELLED: { label: 'Anulado',       cls: 'text-error',    dotCls: 'bg-error' },
    };

    function getStatusBadgeClass(status: string) {
        if (status === 'DELIVERED' && !order.is_paid) return 'bg-fuchsia-500 text-white border-transparent';
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

    function getOrderProgress(order: any) {
        const items = order.items ?? [];
        const active = items.filter((i: any) => i.status !== 'CANCELLED');
        if (active.length === 0) return 100;
        const done = active.filter((i: any) => i.status === 'READY' || i.status === 'DELIVERED').length;
        return Math.round((done / active.length) * 100);
    }

    function calculateTotal(order: any) {
        return order.items?.reduce((sum: number, item: any) => sum + (item.unit_price * item.quantity), 0) || 0;
    }

    function getTimeAgo(dateStr: string) {
        const diffMins = Math.floor((Date.now() - new Date(dateStr).getTime()) / 60000);
        if (diffMins < 1) return 'ahora';
        if (diffMins < 60) return `${diffMins} min`;
        return `${Math.floor(diffMins / 60)}h ${diffMins % 60}m`;
    }

    let progress = $derived(getOrderProgress(order));
    let isFinished = $derived(order.status === 'PAID' || order.status === 'DELIVERED' || order.status === 'CANCELLED');

    let subtotal = $derived(calculateTotal(order));
    let taxRate = $derived(appState.settings?.tax_rate || 0.16);
    let taxAmount = $derived(subtotal * taxRate);
    let finalTotal = $derived(subtotal + taxAmount);

    let glow = $derived(
        order.status === 'PENDING' ? 'shadow-[0_0_25px_var(--tw-shadow-color)] shadow-warning/40 border-warning/30' : 
        order.status === 'PREPARING' ? 'shadow-[0_0_25px_var(--tw-shadow-color)] shadow-primary/40 border-primary/30' : 
        order.status === 'READY' ? 'shadow-[0_0_25px_var(--tw-shadow-color)] shadow-success/40 border-success/30' : 
        (order.status === 'DELIVERED' && !order.is_paid) ? 'shadow-[0_0_25px_var(--tw-shadow-color)] shadow-fuchsia-500/40 border-fuchsia-500/30' :
        order.status === 'CANCELLED' ? 'shadow-[0_0_25px_var(--tw-shadow-color)] shadow-error/40 border-error/30' : 
        'shadow-sm border-base-content/5'
    );
</script>

<div class="card bg-base-100/60 backdrop-blur-xl hover:-translate-y-1 transition-all duration-300 flex flex-col rounded-3xl border relative overflow-hidden group {glow}">
    <div class="absolute inset-0 bg-gradient-to-br from-base-content/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
    <div class="card-body p-6 flex flex-col justify-start gap-0 z-10 h-full">
        <!-- Contenedor superior para agrupar todo arriba -->
        <div class="flex flex-col gap-0 flex-none">
            <!-- ── Cabecera de la tarjeta ──────────────────────── -->
            <div class="flex justify-between items-start mb-3">
                <div class="flex flex-col gap-1">
                    <span class="text-xs font-black uppercase tracking-widest opacity-50 px-2 py-1 bg-base-200 rounded w-fit">
                        #{order.id}
                    </span>
                    {#if order.is_paid}
                        <span class="badge badge-success badge-xs font-black text-[9px] border-none py-1 px-2">PAGADO</span>
                    {/if}
                </div>
                <div class="flex flex-col items-end gap-1">
                    <span class="badge badge-sm font-bold {getStatusBadgeClass(order.status)} p-3">
                        {orderStatusLabel[order.status] ?? order.status}
                    </span>
                    <span class="text-[10px] opacity-50 font-semibold uppercase">{getTimeAgo(order.created_at)}</span>
                </div>
            </div>

            <div class="flex justify-between items-start">
                <div>
                    <h3 class="text-xl font-bold leading-tight">
                        {order.table_id ? `Mesa ${order.table_id}` : 'Mostrador'}
                    </h3>
                    <p class="text-xs opacity-60 uppercase font-black tracking-tight mt-0.5 mb-2">
                        {order.type === 'DINE_IN' ? 'Comedor' : 'Para Llevar'} • {new Date(order.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                    </p>
                    <!-- ── Badges de actor: mesero y cocinero ─────────────── -->
                    <div class="flex flex-wrap gap-1 mt-1">
                        {#if order.waiter_name}
                            <span class="inline-flex items-center gap-1 text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full bg-info/15 text-info border border-info/20">
                                🤵 {order.waiter_name}
                            </span>
                        {/if}
                        {#if order.cook_name && view === 'kitchen'}
                            <span class="inline-flex items-center gap-1 text-[9px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full bg-warning/15 text-warning border border-warning/20">
                                👨‍🍳 {order.cook_name}
                            </span>
                        {/if}
                    </div>
                </div>
            </div>

            <!-- ── Progreso global (Visible si no está terminado) ── -->
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
                <div class="flex flex-col gap-2 mb-4 overflow-y-auto elegant-scroll max-h-72 pr-2">
                    {#each order.items as item}
                        {@const cfg = itemStatusConfig[item.status ?? 'PENDING'] ?? itemStatusConfig['PENDING']}
                        <div class="flex flex-col p-3 rounded-xl border {
                            item.status === 'CANCELLED' ? 'opacity-40 bg-error/5 border-error/20 grayscale' :
                            item.status === 'READY'     ? 'bg-success/10 border-success/20 shadow-sm' :
                            item.status === 'DELIVERED' ? 'bg-fuchsia-500/5 border-fuchsia-500/20 opacity-80' :
                            item.status === 'PREPARING' ? 'bg-primary/5 border-primary/20' :
                            'bg-base-200/50 border-base-300/50'
                        }">
                            
                            <div class="flex items-start gap-2">
                                <!-- Indicador de color -->
                                <div class="mt-1.5 w-2 h-2 rounded-full shrink-0 {cfg.dotCls}"></div>

                                <!-- Nombre + variantes/modificadores -->
                                <div class="flex-1 min-w-0">
                                    <div class="flex items-center gap-2 flex-wrap">
                                        <span class="text-sm md:text-base font-bold leading-tight {item.status === 'CANCELLED' ? 'line-through' : ''}">
                                            {item.quantity}× {item.product?.name ?? 'Producto'}
                                        </span>
                                        {#if view === 'kitchen' && item.product?.recipe_markdown}
                                            {@const recipeKey = `${order.id}-${item.id}`}
                                            {@const hasProgress = activeRecipes[recipeKey] && Object.values(activeRecipes[recipeKey]).some(v => v)}
                                            {@const timers = activeTimers[recipeKey] || {}}
                                            {@const hasRunningTimer = Object.values(timers).some((t: any) => t.running)}
                                            {@const hasFinishedTimer = Object.values(timers).some((t: any) => t.finished)}
                                            
                                            <Button
                                                variant={hasFinishedTimer ? "error" : (hasRunningTimer || hasProgress ? "primary" : "ghost")}
                                                size="xs"
                                                onclick={() => onViewRecipe?.(order.id, item.id, item.product.name, item.product.recipe_markdown)}
                                                id="recipe-btn-{item.id}"
                                                title="Ver receta de preparación"
                                                class="{(hasRunningTimer || hasProgress || hasFinishedTimer) ? 'opacity-100 ring-2 ring-primary/30' : 'opacity-60 hover:opacity-100'} py-0 h-6 min-h-6 text-[10px] relative {hasFinishedTimer ? 'animate-bounce' : ''}"
                                            >
                                                📖 {hasFinishedTimer ? '¡LISTO!' : 'Receta'}
                                                {#if hasRunningTimer || hasProgress || hasFinishedTimer}
                                                    <span class="absolute -top-1 -right-1 flex h-2 w-2">
                                                        <span class="animate-ping absolute inline-flex h-full w-full rounded-full {hasFinishedTimer ? 'bg-error' : 'bg-primary'} opacity-75"></span>
                                                        <span class="relative inline-flex rounded-full h-2 w-2 {hasFinishedTimer ? 'bg-error' : 'bg-primary'}"></span>
                                                    </span>
                                                {/if}
                                            </Button>
                                        {/if}
                                    </div>
                                    
                                    <div class="flex flex-wrap items-center gap-1 mt-1">
                                        {#if item.variant}
                                            <span class="badge badge-primary badge-outline badge-xs font-bold text-[9px] uppercase tracking-wider">{item.variant.measure.name}</span>
                                        {/if}
                                        {#if item.modifiers && item.modifiers.length > 0}
                                            {#each item.modifiers as mod}
                                                <span class="font-semibold text-[9px] text-base-content/70 bg-base-300/50 px-1.5 py-0.5 rounded-md uppercase tracking-tight">+ {mod.name}</span>
                                            {/each}
                                        {/if}
                                    </div>
                                </div>

                                <!-- Estado + botones (Órdenes y Cocina) -->
                                <div class="flex flex-col items-end gap-1 shrink-0">
                                    <span class="text-[10px] font-black uppercase tracking-tight {cfg.cls}">
                                        {cfg.label}
                                    </span>

                                    <!-- Acciones por vista -->
                                    {#if view === 'orders' && canManageKitchenStatus && !isFinished}
                                        {#if item.status === 'PENDING' || item.status === 'PREPARING'}
                                            <Button
                                                size="xs"
                                                variant={item.status === 'PENDING' ? 'outline' : 'primary'}
                                                circle
                                                onclick={() => onItemComplete?.(order, item)}
                                                title={item.status === 'PENDING' ? 'Empezar preparación' : 'Marcar como listo'}
                                                id="advance-item-{item.id}"
                                                class={item.status === 'PENDING' ? 'text-warning border-warning' : ''}
                                            >
                                                {item.status === 'PENDING' ? '▶' : '✓'}
                                            </Button>
                                        {:else if item.status === 'READY'}
                                            <Button
                                                size="xs"
                                                variant="success"
                                                circle
                                                onclick={() => onItemComplete?.(order, item)}
                                                title="Entregar este platillo"
                                                id="deliver-item-{item.id}"
                                            >
                                                🚚
                                            </Button>
                                        {/if}
                                    {/if}

                                    {#if view === 'kitchen'}
                                        <div class="flex gap-1.5 mt-1">
                                            {#if item.status === 'PENDING'}
                                                <Button variant="outline" danger square size="xs" onclick={() => onItemCancel?.(order, item)} title="Anular platillo">
                                                    🗑️
                                                </Button>
                                                <Button variant="secondary" size="xs" onclick={() => onItemComplete?.(order, item)}>
                                                    Empezar
                                                </Button>
                                            {:else if item.status === 'PREPARING'}
                                                <Button variant="primary" size="xs" onclick={() => onItemComplete?.(order, item)}>
                                                    ✓ Listo
                                                </Button>
                                            {/if}
                                        </div>
                                    {/if}
                                </div>
                            </div>
                        </div>
                    {/each}
                </div>
            {:else}
                <div class="py-3 text-center opacity-30 text-xs italic">— sin artículos —</div>
            {/if}

            {#if view === 'kitchen' && order.external_reference}
                <p class="text-[10px] text-accent font-bold mb-2">REF: {order.external_reference}</p>
            {/if}
        </div>

        <!-- ── Footer: Total + Aciones Globales ────────────────────────────── -->
        {#if view === 'orders'}
            <!-- FOOTER DE ORDENES -->
            <div class="pt-3 border-t border-base-200 flex flex-col mt-auto shrink-0 gap-3">
                <div class="flex flex-col px-1 w-full gap-0.5">
                    <div class="flex justify-between items-center text-[10px] font-bold uppercase opacity-50 tracking-wider">
                        <span>Subtotal</span>
                        <span>${subtotal.toFixed(2)}</span>
                    </div>
                    <div class="flex justify-between items-center text-[10px] font-bold uppercase opacity-50 tracking-wider pb-1.5 border-b border-base-content/5">
                        <span>IVA ({(taxRate * 100).toFixed(0)}%)</span>
                        <span>${taxAmount.toFixed(2)}</span>
                    </div>
                    <div class="flex justify-between items-end pt-1.5">
                        <span class="text-[12px] font-bold uppercase opacity-70 tracking-wider mb-0.5">Total</span>
                        <span class="font-mono text-2xl font-black text-primary leading-none">
                            ${finalTotal.toFixed(2)}
                        </span>
                    </div>
                </div>
                
                <div class="flex justify-between items-center gap-2 pt-2 border-t border-base-200/50">
                    <!-- Text Buttons (Cobrar / Entregar) -->
                    <div class="flex gap-2 items-center flex-wrap">
                        <!-- Botón de Cobrar (Solo si no está pagado, y no está cancelado) -->
                        {#if onCharge && !order.is_paid && order.status !== 'CANCELLED'}
                            <Button variant="primary" size="sm" class="shadow-sm font-bold" onclick={() => onCharge(order)}>
                                Cobrar
                            </Button>
                        {/if}

                        <!-- Botón de Entregar (Solo habilitado si TODO está listo/entregado) -->
                        {#if onDeliver && order.status !== 'DELIVERED' && order.status !== 'CANCELLED'}
                            <Button 
                                variant="success" 
                                size="sm" 
                                class="shadow-sm font-bold" 
                                disabled={progress < 100}
                                title={progress < 100 ? 'Todos los platillos deben estar listos para entregar la orden completa' : 'Entregar pedido completo'}
                                onclick={() => onDeliver(order.id)}
                            >
                                Entregar
                            </Button>
                        {/if}
                    </div>

                    <!-- Icon Buttons (Imprimir / Cancelar) forced to stay in one line -->
                    <div class="flex gap-1.5 items-center shrink-0 flex-nowrap ml-auto">
                        {#if order.type === 'DINE_IN' && !isFinished}
                            <Button variant="ghost" size="sm" square onclick={() => onTransferOrder?.(order)} title="Mover Mesa">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
                                </svg>
                            </Button>
                        {/if}

                        <Button variant="ghost" size="sm" square onclick={() => onPrint?.(order.id)} isLoading={printingOrderId === order.id} title="Imprimir Ticket">
                            🖨️
                        </Button>

                        {#if onCancelOrder && order.status !== 'PAID' && order.status !== 'DELIVERED' && order.status !== 'CANCELLED'}
                            <Button variant="ghost" size="sm" danger square onclick={() => onCancelOrder(order)} title={order.items && order.items.length > 0 ? "Cancelar Pedido" : "Eliminar Pedido Vacío"}>
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                            </Button>
                        {/if}
                    </div>
                </div>
            </div>
        {:else}
            <!-- FOOTER DE COCINA -->
            <div class="card-actions flex gap-2 mt-auto pt-4 border-t border-base-200">
                {#if order.status === 'PENDING'}
                    <Button variant="outline" danger square onclick={() => onCancelOrder?.(order)} title="Anular toda la orden">
                        🗑️
                    </Button>
                {/if}
                
                <Button variant="outline" square onclick={() => onPrint?.(order.id)} isLoading={printingOrderId === order.id} title="Imprimir comanda">
                    🖨️
                </Button>

                <Button variant={order.status === 'PENDING' ? 'secondary' : 'primary'} class="flex-1 text-base md:text-lg font-black" onclick={() => onCompleteOrder?.(order)}>
                    {order.status === 'PENDING' ? 'Empezar Toda la Orden' : '✓ Orden Lista'}
                </Button>
            </div>
        {/if}
    </div>
</div>
