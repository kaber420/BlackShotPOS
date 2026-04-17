<script lang="ts">
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { TableService, type Table } from '$lib/api/tables';
    import { OrderService, OrderType, OrderStatus } from '$lib/api/orders';
    import TableModal from '$lib/components/TableModal.svelte';
    import TableSummaryModal from '$lib/components/TableSummaryModal.svelte';
    import { setActiveTable, loadOrderToCart, appState } from '$lib/app_state.svelte';
    import Button from '$lib/components/ui/Button.svelte';
    
    let tables = $state<Table[]>([]);
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
        await refreshTables();
    });

    async function refreshTables() {
        isLoading = true;
        try {
            // En modo admin queremos ver todas las mesas, incluyendo las inactivas si existen
            tables = await TableService.getAll(true);
        } catch (e) {
            console.error("Error loading tables", e);
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
                // Find existing order for this table
                const activeOrders = await OrderService.getAll(OrderStatus.PENDING); // Or filter by multiple statuses if needed
                const tableOrder = activeOrders.find(o => o.table_id === table.id);
                
                if (tableOrder) {
                    summaryOrder = tableOrder;
                    summaryTable = table;
                    isSummaryOpen = true;
                } else {
                    // Fallback: If occupied but no order found, maybe it's preparing?
                    const preparingOrders = await OrderService.getAll(OrderStatus.PREPARING);
                    const tableOrderPrep = preparingOrders.find(o => o.table_id === table.id);
                    if (tableOrderPrep) {
                        summaryOrder = tableOrderPrep;
                        summaryTable = table;
                        isSummaryOpen = true;
                    } else {
                        alert("Mesa ocupada pero no se encontró orden activa.");
                    }
                }
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
</script>

<div class="p-6 md:p-8 lg:p-10 flex flex-col gap-8 w-full flex-1 min-h-0 overflow-y-auto">
    <header class="flex flex-col gap-2">
        <div class="flex justify-between items-center">
            <div>
                <h1 class="text-4xl font-extrabold tracking-tight">Mesas y Salón</h1>
                <p class="text-lg opacity-70">Monitorea la ocupación y gestiona la asignación de mesas.</p>
            </div>
            <div class="flex items-center gap-3">
                <Button 
                    variant={adminMode ? 'primary' : 'outline'}
                    size="md"
                    class="gap-2" 
                    onclick={() => { adminMode = !adminMode; refreshTables(); }}
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

                <Button variant="ghost" circle size="md" onclick={refreshTables} aria-label="Actualizar mesas">
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
        <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 2xl:grid-cols-10 gap-6">
            {#each tables as table}
                <!-- svelte-ignore a11y_click_events_have_key_events -->
                <div 
                    role="button"
                    tabindex="0"
                    class="card aspect-square shadow-xl bg-base-100 transition-all border-2 { table.is_active ? (table.status === 'Occupied' ? 'border-error hover:scale-105 cursor-pointer active:scale-95' : 'border-success hover:scale-105 cursor-pointer active:scale-95') : 'border-base-300 opacity-50 grayscale cursor-not-allowed' }"
                    onclick={() => table.is_active && handleTableClick(table)}
                >
                    <div class="card-body p-4 items-center justify-center text-center">
                        <span class="text-3xl font-black">{table.number}</span>
                        <p class="text-xs font-bold uppercase tracking-widest opacity-60">MESA</p>
                        
                        {#if adminMode}
                            <div class="flex gap-1 mt-4">
                                <Button variant="ghost" size="xs" class="text-primary" onclick={(e) => { e.stopPropagation(); openEditModal(table); }}>Editar</Button>
                                <Button variant="ghost" size="xs" danger onclick={(e) => { e.stopPropagation(); toggleTableActive(table); }}>
                                    {table.is_active ? 'Eliminar' : 'Activar'}
                                </Button>
                            </div>
                        {:else}
                            {#if !table.is_active}
                                <div class="badge badge-ghost font-bold mt-2">INACTIVA</div>
                            {:else if table.status === 'Occupied'}
                                <div class="badge badge-error text-white font-bold mt-2">OCUPADA</div>
                            {:else if table.status === 'Free'}
                                <div class="badge badge-success text-white font-bold mt-2">LIBRE</div>
                            {:else}
                                <div class="badge badge-ghost font-bold mt-2">{table.status}</div>
                            {/if}
                        {/if}
                        
                        {#if table.location}
                            <p class="text-[9px] mt-2 opacity-40 uppercase font-bold tracking-tight">{table.location}</p>
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
