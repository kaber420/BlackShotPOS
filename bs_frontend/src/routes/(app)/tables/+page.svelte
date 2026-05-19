<script lang="ts">
    import { onMount, onDestroy } from 'svelte';
    import { goto } from '$app/navigation';
    import { TableService, type Table } from '$lib/api/tables';
    import { OrderService, OrderType, OrderStatus, type Order } from '$lib/api/orders';
    import TableModal from '$lib/components/TableModal.svelte';
    import TableSummaryModal from '$lib/components/TableSummaryModal.svelte';
    import ReservationModal from '$lib/components/ReservationModal.svelte';
    import ReservationManager from '$lib/components/ReservationManager.svelte';
    import { setActiveTable, loadOrderToCart, appState } from '$lib/app_state.svelte';
    import Button from '$lib/components/ui/Button.svelte';
    import Toolbar from '$lib/components/ui/Toolbar.svelte';
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
        const diff = Math.max(0, Math.floor((now.getTime() - start.getTime()) / 60000));
        
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

    // Reservation Modal
    let isReservationModalOpen = $state(false);
    let reservationInitialTableId = $state<number | null>(null);

    // Filters
    let searchQuery = $state('');
    let selectedLocation = $state<string | null>(null);
    let locations = $derived<string[]>(Array.from(new Set(tables.map(t => t.location).filter(l => l && l.trim() !== ''))) as string[]);
    let showReservations = $state(false);
    
    let filteredTables = $derived.by(() => {
        let result = selectedLocation ? tables.filter(t => t.location === selectedLocation) : tables;
        if (searchQuery.trim() !== '') {
            const q = searchQuery.toLowerCase();
            result = result.filter(t => 
                t.number.toString().includes(q) || 
                t.location?.toLowerCase().includes(q)
            );
        }
        return result;
    });

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

    function openReservationModal(tableId?: number) {
        reservationInitialTableId = tableId || null;
        isReservationModalOpen = true;
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
        } else if (table.status === 'Reserved') {
            // Al hacer click en una mesa reservada, podríamos abrir el manager o algo
            // Pero como ya lo tenemos en el sidebar, tal vez no sea necesario redirigir
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
        
        // Efecto base de hover y click
        const baseClasses = 'hover:scale-105 active:scale-95 cursor-pointer transition-all duration-300';

        if (table.waiter_requested) {
            return `shadow-[0_0_25px_var(--tw-shadow-color)] shadow-amber-500/50 border-amber-500/60 bg-amber-500/5 ${baseClasses}`;
        }
        if (table.bill_requested) {
            return `shadow-[0_0_25px_var(--tw-shadow-color)] shadow-info/50 border-info/60 bg-info/5 ${baseClasses}`;
        }

        const order = getTableOrder(table.id);

        if (table.status === 'Reserved') {
            return `border-info/40 shadow-info/10 ${baseClasses}`;
        }

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

<div class="flex h-full w-full overflow-hidden bg-base-200">
    <!-- Sidebar de Reservas (Compacto) -->
    {#if showReservations}
        <aside class="w-80 bg-base-100 border-r border-base-300 p-6 flex flex-col gap-6 overflow-y-auto elegant-scroll shadow-inner">
            <ReservationManager compact={true} onSave={refreshTables} />
        </aside>
    {/if}

    <!-- Área Principal del Salón -->
    <div class="flex-1 p-6 md:p-8 lg:p-10 flex flex-col gap-8 w-full min-h-0 overflow-y-auto elegant-scroll">
        <Toolbar title="Mesas">
            {#snippet left()}
                <!-- Search Input -->
                <div class="relative w-full md:w-48 lg:w-64 shrink-0 hidden md:block">
                    <input 
                        type="text" 
                        placeholder="Buscar mesa o zona..." 
                        bind:value={searchQuery}
                        class="input input-sm w-full rounded-xl bg-base-200/40 backdrop-blur-md border border-base-300 focus:ring-2 focus:ring-primary/20 transition-all font-bold text-sm"
                    />
                </div>

                <!-- Dropdown de Ubicación -->
                <div class="dropdown dropdown-bottom">
                    <div tabindex="0" role="button" class="btn btn-sm bg-base-100 border-2 border-base-200 px-4 font-black flex items-center gap-2 hover:border-primary/30 transition-all rounded-xl shadow-sm">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                        Zona: 
                        <span class="text-primary">
                            {selectedLocation || 'Todas'}
                        </span>
                    </div>
                    <div tabindex="0" class="dropdown-content z-[50] card card-compact w-64 p-2 shadow-2xl bg-base-100 border border-base-200 mt-3 rounded-2xl">
                        <div class="p-3 border-b border-base-200 mb-2 flex justify-between items-center">
                            <span class="text-[10px] uppercase font-black opacity-40 tracking-widest">Filtrar por Zona</span>
                        </div>
                        <div class="max-h-60 overflow-y-auto space-y-1 p-1">
                            <button class="w-full text-left p-3 rounded-xl hover:bg-base-200 transition-colors font-bold text-sm {selectedLocation === null ? 'bg-primary/10 text-primary' : ''}" onclick={() => selectedLocation = null}>
                                Todas las zonas
                            </button>
                            {#each locations as loc}
                                <button class="w-full text-left p-3 rounded-xl hover:bg-base-200 transition-colors font-bold text-sm {selectedLocation === loc ? 'bg-primary/10 text-primary' : ''}" onclick={() => selectedLocation = loc}>
                                    {loc}
                                </button>
                            {/each}
                        </div>
                    </div>
                </div>
            {/snippet}

            {#snippet right()}
                <Button 
                    variant={showReservations ? 'primary' : 'outline'}
                    size="sm"
                    class="gap-2 rounded-xl" 
                    onclick={() => showReservations = !showReservations}
                >
                    <svelte:fragment slot="icon">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2-2v12a2 2 0 002 2z" />
                        </svg>
                    </svelte:fragment>
                    Reservas
                </Button>

                <Button 
                    variant={adminMode ? 'primary' : 'outline'}
                    size="sm"
                    class="gap-2 rounded-xl" 
                    onclick={() => { adminMode = !adminMode; }}
                >
                    <svelte:fragment slot="icon">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                        </svg>
                    </svelte:fragment>
                    {adminMode ? 'Salir Config.' : 'Configurar'}
                </Button>

                {#if adminMode}
                    <Button variant="primary" size="sm" class="gap-2 rounded-xl" onclick={openCreateModal}>
                        <svelte:fragment slot="icon">
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                            </svg>
                        </svelte:fragment>
                        Mesa
                    </Button>
                {/if}

                <Button variant="ghost" circle size="sm" onclick={() => refreshTables(true)} aria-label="Actualizar mesas">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                </Button>
            {/snippet}
        </Toolbar>

        <!-- Mobile Search Input -->
        <div class="md:hidden w-full relative">
            <input 
                type="text" 
                placeholder="Buscar mesa o zona..." 
                bind:value={searchQuery}
                class="input input-md w-full rounded-xl bg-base-200/40 backdrop-blur-md shadow-sm border border-base-200 focus:ring-2 focus:ring-primary/20 transition-all font-bold"
            />
        </div>

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
                {#each filteredTables as table}
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

                        <!-- Alerta de "Mesero / Cuenta" desde IoT -->
                        {#if table.waiter_requested || table.bill_requested}
                            <div class="absolute -top-4 -left-3 z-20 flex flex-col gap-1.5 pointer-events-auto">
                                {#if table.waiter_requested}
                                    <!-- svelte-ignore a11y_click_events_have_key_events -->
                                    <div class="badge bg-amber-500 hover:bg-amber-600 text-white font-black shadow-lg shadow-amber-500/40 border-none py-3.5 px-4 flex gap-1.5 items-center cursor-pointer animate-pulse transition-all hover:scale-105" 
                                         role="button" tabindex="0"
                                         onclick={(e) => { e.stopPropagation(); TableService.clearRequests(table.id); }}>
                                        <span class="text-xs">🛎️</span>
                                        <span class="text-[9px] tracking-wider font-extrabold">MESERO</span>
                                    </div>
                                {/if}
                                {#if table.bill_requested}
                                    <!-- svelte-ignore a11y_click_events_have_key_events -->
                                    <div class="badge bg-info hover:bg-info/80 text-white font-black shadow-lg shadow-info/40 border-none py-3.5 px-4 flex gap-1.5 items-center cursor-pointer animate-pulse transition-all hover:scale-105"
                                         role="button" tabindex="0"
                                         onclick={(e) => { e.stopPropagation(); TableService.clearRequests(table.id); }}>
                                        <span class="text-xs">💵</span>
                                        <span class="text-[9px] tracking-wider font-extrabold">CUENTA</span>
                                    </div>
                                {/if}
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
                                {:else if table.status === 'Reserved'}
                                    <div class="flex flex-col items-center gap-1 mt-4">
                                        <div class="badge badge-info text-white font-black">RESERVADA</div>
                                        <p class="text-[9px] font-bold opacity-60">Check-in pendiente</p>
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

<ReservationModal
    isOpen={isReservationModalOpen}
    initialTableId={reservationInitialTableId}
    onClose={() => isReservationModalOpen = false}
    onSave={refreshTables}
/>

