<script lang="ts">
    import { onMount, onDestroy } from 'svelte';
    import { goto } from '$app/navigation';
    import { TableService, type Table } from '$lib/api/tables';
    import { OrderService, OrderType, OrderStatus, type Order } from '$lib/api/orders';
    import TableModal from '$lib/components/TableModal.svelte';
    import TableSummaryModal from '$lib/components/TableSummaryModal.svelte';
    import { setActiveTable, loadOrderToCart, appState } from '$lib/app_state.svelte';
    import Button from '$lib/components/ui/Button.svelte';
    import { posSocket } from '$lib/pos_socket.svelte';
    
    let now = $state(new Date());

    onMount(() => {
        const interval = setInterval(() => {
            now = new Date();
        }, 30000); // Actualizar cada 30 segundos
        return () => clearInterval(interval);
    });

    function getDuration(occupiedAt: string | undefined): string {
        if (!occupiedAt) return '';
        const start = new Date(occupiedAt);
        const diff = Math.floor((now.getTime() - start.getTime()) / 60000);
        
        if (diff < 60) return `${diff}m`;
        const hours = Math.floor(diff / 60);
        const mins = diff % 60;
        return `${hours}h ${mins}m`;
    }
    
    let tables = $derived<Table[]>(posSocket.tables.length > 0 ? posSocket.tables : []);
    
    // Filtramos solo las órdenes activas que nos interesan para el dashboard desde recentOrders
    let activeOrders = $derived<Order[]>((posSocket.recentOrders || []).filter(o => 
        o.status === OrderStatus.PENDING || 
        o.status === OrderStatus.PREPARING || 
        o.status === OrderStatus.READY
    ));
    
    let isLoading = $state(true);
    let adminMode = $state(false);
    
    // Modal state
    let isModalOpen = $state(false);
    let editingTable = $state<Table | null>(null);

    // Summary Modal state
    let isSummaryOpen = $state(false);
    let summaryTable = $state<Table | null>(null);
    let summaryOrder = $state<any>(null);

    onMount(async () => {
        // Inicializar Websocket
        posSocket.subscribe("tables");
        posSocket.subscribe("recent_orders");
        
        await refreshTables();
    });

    onDestroy(() => {
        posSocket.unsubscribe("tables");
        posSocket.unsubscribe("recent_orders");
    });

    async function refreshTables(force = false) {
        // Solo saltamos la carga si el socket tiene datos Y no es un refresh forzado
        if (!force && posSocket.tables.length > 0) {
            isLoading = false;
            return;
        }

        isLoading = true;
        try {
            // Cargar inicial (solo si es la primera vez que entramos y el socket no trajo nada aun)
            const [fetchedTables, fetchedOrders] = await Promise.all([
                TableService.getAll(true),
                OrderService.getAll()
            ]);
            // Inicializar el socket stores si está vacío
            if (posSocket.tables.length === 0) posSocket.tables = fetchedTables;
            if (posSocket.recentOrders.length === 0) posSocket.recentOrders = fetchedOrders;
        } catch (e) {
            console.error("Error loading table data", e);
        } finally {
            isLoading = false;
        }
    }

    function openEditModal(table: Table) {
        editingTable = table;
        isModalOpen = true;
    }

    function openCreateModal() {
        editingTable = null;
        isModalOpen = true;
    }

    async function toggleTableActive(table: Table) {
        const action = table.is_active ? 'desactivar' : 'activar';
        if (!confirm(`¿Estás seguro de que deseas ${action} la mesa ${table.number}?`)) return;
        
        try {
            await TableService.update(table.id, { is_active: !table.is_active });
            await refreshTables();
        } catch (e) {
            alert(`Error al cambiar estado de la mesa: ${e}`);
        }
    }

    async function handleTableClick(table: Table) {
        if (adminMode) {
            openEditModal(table);
            return;
        }

        if (table.status === 'Free') {
            setActiveTable(table, null);
            goto('/');
        } else if (table.status === 'Occupied') {
            try {
                // Buscamos la orden en el estado reactivo del socket primero (es instantáneo)
                let tableOrder = activeOrders.find(o => o.table_id === table.id);
                
                // Si no está en el socket (raro), hacemos un fetch de seguridad buscando cualquier orden activa
                if (!tableOrder) {
                    const allActive = await OrderService.getAll(); // Sin filtro trae todo lo PENDING/PREPARING/READY/etc
                    tableOrder = allActive.find(o => o.table_id === table.id && o.status !== OrderStatus.PAID);
                }
                
                summaryOrder = tableOrder || null;
                summaryTable = table;
                isSummaryOpen = true;
            } catch (e) {
                alert(`Error al cargar orden de la mesa: ${e}`);
            }
        }
    }

    function handleSummaryCheckout() {
        if (summaryOrder && summaryTable) {
            loadOrderToCart(summaryOrder);
            appState.activeTable = summaryTable;
            isSummaryOpen = false;
            appState.cartVisible = true;
        }
    }

    function handleSummaryAddMore() {
        if (summaryOrder && summaryTable) {
            loadOrderToCart(summaryOrder);
            appState.activeTable = summaryTable;
            isSummaryOpen = false;
            goto('/');
        }
    }

    // Helper functions for table UI
    function getTableOrder(tableId: number) {
        return activeOrders.find(o => o.table_id === tableId);
    }

    function hasReadyItems(order: Order) {
        // Un ítem está listo si su estado individual es READY pero la orden global aún no
        return order.items?.some(i => i.status === 'READY') ?? false;
    }

    function getTableGlow(table: Table) {
        if (!table.is_active) return 'border-base-300 opacity-50 grayscale cursor-not-allowed';
        
        const order = getTableOrder(table.id);
        
        // Efecto base de hover y click
        const baseClasses = 'hover:scale-105 active:scale-95 cursor-pointer transition-all duration-300';

        if (!order) {
            return table.status === 'Occupied' 
                ? `border-error/40 shadow-error/10 ${baseClasses}` 
                : `border-success/40 shadow-success/10 ${baseClasses}`;
        }

        switch (order.status) {
            case OrderStatus.PENDING:
                return `shadow-[0_0_20px_var(--tw-shadow-color)] shadow-warning/40 border-warning/50 bg-warning/5 ${baseClasses}`;
            case OrderStatus.PREPARING:
                return `shadow-[0_0_20px_var(--tw-shadow-color)] shadow-primary/40 border-primary/50 bg-primary/5 ${baseClasses}`;
            case OrderStatus.READY:
                return `shadow-[0_0_30px_var(--tw-shadow-color)] shadow-success/60 border-success/60 bg-success/10 animate-pulse ${baseClasses}`;
            default:
                return `border-base-300 ${baseClasses}`;
        }
    }
</script>

<div class="p-6 md:p-8 lg:p-10 flex flex-col gap-8 w-full flex-1 min-h-0 overflow-y-auto">
    <header class="flex flex-col gap-2">
        <div class="flex justify-between items-center">
            <div>
                <h1 class="text-4xl font-extrabold tracking-tight">Mesas y Salón</h1>
                <p class="text-lg opacity-70">Monitorea la ocupación y gestiona la asignación de mesas.</p>
            </div>
            <div class="flex items-center gap-3">
                <!-- Badge de conexión -->
                <div class="badge {posSocket.status === 'open' ? 'badge-success' : posSocket.status === 'connecting' ? 'badge-warning' : 'badge-error'} gap-2 p-3 font-bold opacity-80" title="Estado de conexión en tiempo real">
                    {#if posSocket.status === 'open'}
                        <span class="relative flex h-2 w-2">
                            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75"></span>
                            <span class="relative inline-flex rounded-full h-2 w-2 bg-success"></span>
                        </span>
                    {/if}
                    {posSocket.status === 'open' ? 'EN VIVO' : posSocket.status === 'connecting' ? 'CONECTANDO...' : 'DESCONECTADO'}
                </div>

                <Button 
                    variant={adminMode ? 'primary' : 'outline'}
                    size="md"
                    class="gap-2" 
                    onclick={() => { adminMode = !adminMode; }}
                >
                    <svelte:fragment slot="icon">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                    </svelte:fragment>
                    {adminMode ? 'Salir Configuración' : 'Configurar Salón'}
                </Button>

                {#if adminMode}
                    <Button variant="primary" size="md" class="gap-2" onclick={openCreateModal}>
                        <svelte:fragment slot="icon">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                            </svg>
                        </svelte:fragment>
                        Nueva Mesa
                    </Button>
                {/if}

                <Button variant="ghost" circle size="md" onclick={() => refreshTables(true)} aria-label="Actualizar mesas">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                </Button>
            </div>
        </div>
    </header>

    {#if isLoading}
        <div class="flex justify-center py-20">
            <span class="loading loading-spinner loading-lg text-primary"></span>
        </div>
    {:else if tables.length === 0}
        <div class="flex flex-col items-center justify-center py-20 bg-base-200 rounded-2xl border-2 border-dashed border-base-300">
            <p class="text-xl font-bold opacity-30">No hay mesas configuradas</p>
            <p class="text-sm opacity-20">Ve al panel de administración para añadir mesas.</p>
        </div>
    {:else}
        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 2xl:grid-cols-8 gap-8">
            {#each tables as table}
                {@const order = getTableOrder(table.id)}
                {@const readyAlert = order && order.status !== 'READY' && hasReadyItems(order)}
                <!-- svelte-ignore a11y_click_events_have_key_events -->
                <div 
                    role="button"
                    tabindex="0"
                    class="card aspect-square shadow-xl bg-base-100/60 backdrop-blur-xl rounded-[2.5rem] border-2 relative overflow-visible group {getTableGlow(table)}"
                    onclick={() => table.is_active && handleTableClick(table)}
                >
                    <!-- Alerta de "Listo" -->
                    {#if readyAlert}
                        <div class="absolute -top-3 -right-3 z-20 animate-bounce">
                            <div class="badge badge-success text-white font-black shadow-lg shadow-success/40 border-none py-3 px-4 flex gap-1 items-center">
                                <span class="text-lg">🔔</span>
                                <span class="text-xs">LISTO</span>
                            </div>
                        </div>
                    {/if}

                    <div class="card-body p-6 items-center justify-center text-center relative z-10">
                        <span class="text-5xl font-black tracking-tighter mb-1">{table.number}</span>
                        <p class="text-[10px] font-black uppercase tracking-[0.2em] opacity-40">MESA</p>
                        
                        {#if adminMode}
                            <div class="flex flex-col gap-1 mt-4 w-full">
                                <Button variant="ghost" size="xs" class="text-primary w-full" onclick={(e) => { e.stopPropagation(); openEditModal(table); }}>Editar</Button>
                                <Button variant="ghost" size="xs" danger class="w-full" onclick={(e) => { e.stopPropagation(); toggleTableActive(table); }}>
                                    {table.is_active ? 'Eliminar' : 'Activar'}
                                </Button>
                            </div>
                        {:else}
                            {#if !table.is_active}
                                <div class="badge badge-ghost font-bold mt-4 opacity-50">INACTIVA</div>
                            {:else if order}
                                <div class="mt-4 flex flex-col items-center gap-1">
                                    <div class="badge badge-sm font-black border-none {
                                        order.status === 'READY' ? 'bg-success text-white' : 
                                        order.status === 'PREPARING' ? 'bg-primary text-white' : 
                                        'bg-warning text-black'
                                    }">
                                        {order.status === 'READY' ? 'COMPLETO' : 
                                         order.status === 'PREPARING' ? 'COCINANDO' : 'PENDIENTE'}
                                    </div>
                                    {#if order.items}
                                        <p class="text-[10px] font-bold opacity-60">{order.items.length} items</p>
                                    {/if}
                                    {#if table.occupied_at}
                                        <span class="text-[9px] font-black opacity-50 flex items-center gap-1 mt-1">
                                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-2.5 h-2.5">
                                                <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                                            </svg>
                                            {getDuration(table.occupied_at)}
                                        </span>
                                    {/if}
                                </div>
                            {:else if table.status === 'Occupied'}
                                <div class="flex flex-col items-center gap-1 mt-4">
                                    <div class="badge badge-error text-white font-bold">OCUPADA</div>
                                    <span class="text-[10px] font-black opacity-60 flex items-center gap-1">
                                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-2.5 h-2.5">
                                            <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                                        </svg>
                                        {getDuration(table.occupied_at)}
                                    </span>
                                </div>
                            {:else if table.status === 'Free'}
                                <div class="badge badge-outline border-success/40 text-success/70 font-black mt-4 uppercase text-[10px] tracking-widest">LIBRE</div>
                            {:else}
                                <div class="badge badge-ghost font-bold mt-4">{table.status}</div>
                            {/if}
                        {/if}
                        
                        {#if table.location}
                            <p class="absolute bottom-4 text-[9px] opacity-30 uppercase font-black tracking-widest w-full px-4 truncate">{table.location}</p>
                        {/if}
                    </div>
                </div>
            {/each}
        </div>
    {/if}
</div>

<TableModal 
    isOpen={isModalOpen}
    table={editingTable}
    onClose={() => isModalOpen = false}
    onSave={refreshTables}
/>

<TableSummaryModal
    isOpen={isSummaryOpen}
    table={summaryTable}
    order={summaryOrder}
    onClose={() => isSummaryOpen = false}
    onAddMore={handleSummaryAddMore}
    onCheckout={handleSummaryCheckout}
    onActionComplete={refreshTables}
/>
