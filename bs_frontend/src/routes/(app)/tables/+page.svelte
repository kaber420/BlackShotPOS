<script lang="ts">
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { TableService, type Table } from '$lib/api/tables';
    import { OrderService, OrderType, OrderStatus } from '$lib/api/orders';
    import { setActiveTable } from '$lib/app_state.svelte';

    let tables = $state<Table[]>([]);
    let isLoading = $state(true);

    onMount(async () => {
        await refreshTables();
    });

    async function refreshTables() {
        isLoading = true;
        try {
            tables = await TableService.getAll();
        } catch (e) {
            console.error("Error loading tables", e);
        } finally {
            isLoading = false;
        }
    }

    async function handleTableClick(table: Table) {
        if (table.status === 'Free') {
            try {
                // 1. Create a new order for this table
                const order = await OrderService.create({
                    type: OrderType.DINE_IN,
                    table_id: table.id
                });
                
                // 2. Update table status to Occupied (The backend might do this automatically, but let's be sure or assume it does)
                // Assuming backend handles status transition on order creation for a table.
                
                // 3. Set global state and redirect to POS
                setActiveTable(table, order);
                goto('/');
            } catch (e) {
                alert(`Error al abrir mesa: ${e}`);
            }
        } else if (table.status === 'Occupied') {
            try {
                // Find existing order for this table
                const activeOrders = await OrderService.getAll(OrderStatus.PENDING); // Or filter by multiple statuses if needed
                const tableOrder = activeOrders.find(o => o.table_id === table.id);
                
                if (tableOrder) {
                    setActiveTable(table, tableOrder);
                    goto('/');
                } else {
                    // Fallback: If occupied but no order found, maybe it's preparing?
                    const preparingOrders = await OrderService.getAll(OrderStatus.PREPARING);
                    const tableOrderPrep = preparingOrders.find(o => o.table_id === table.id);
                    if (tableOrderPrep) {
                        setActiveTable(table, tableOrderPrep);
                        goto('/');
                    } else {
                        alert("Mesa ocupada pero no se encontró orden activa.");
                    }
                }
            } catch (e) {
                alert(`Error al cargar orden de la mesa: ${e}`);
            }
        }
    }
</script>

<div class="p-6 md:p-8 lg:p-12 max-w-7xl mx-auto flex flex-col gap-8">
    <header class="flex flex-col gap-2">
        <div class="flex justify-between items-center">
            <div>
                <h1 class="text-4xl font-extrabold tracking-tight">Mesas y Salón</h1>
                <p class="text-lg opacity-70">Monitorea la ocupación y gestiona la asignación de mesas.</p>
            </div>
            <button class="btn btn-ghost btn-circle" onclick={refreshTables} aria-label="Actualizar mesas">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
            </button>
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
        <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-6">
            {#each tables as table}
                <button 
                    class="card aspect-square shadow-xl bg-base-100 transition-all border-2 { table.is_active ? (table.status === 'Occupied' ? 'border-error hover:scale-105 cursor-pointer active:scale-95' : 'border-success hover:scale-105 cursor-pointer active:scale-95') : 'border-base-300 opacity-50 grayscale cursor-not-allowed' }"
                    onclick={() => table.is_active && handleTableClick(table)}
                >
                    <div class="card-body p-4 items-center justify-center text-center">
                        <span class="text-3xl font-black">{table.number}</span>
                        <p class="text-xs font-bold uppercase tracking-widest opacity-60">MESA</p>
                        
                        {#if !table.is_active}
                            <div class="badge badge-ghost font-bold mt-2">INACTIVA</div>
                        {:else if table.status === 'Occupied'}
                            <div class="badge badge-error text-white font-bold mt-2">OCUPADA</div>
                        {:else if table.status === 'Free'}
                            <div class="badge badge-success text-white font-bold mt-2">LIBRE</div>
                        {:else}
                            <div class="badge badge-ghost font-bold mt-2">{table.status}</div>
                        {/if}
                        
                        {#if table.location}
                            <p class="text-[9px] mt-2 opacity-40 uppercase font-bold tracking-tight">{table.location}</p>
                        {/if}
                    </div>
                </button>
            {/each}
        </div>
    {/if}
</div>
