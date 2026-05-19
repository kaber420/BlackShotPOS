<script lang="ts">
    import { onMount } from 'svelte';
    import { listActiveSessions, type ShiftInfo } from '$lib/api/shifts';
    import { formatCurrency, formatDateTime } from '$lib/utils';
    import Button from '$lib/components/ui/Button.svelte';
    import { toast } from '$lib/toast.svelte';

    let activeSessions = $state<ShiftInfo[]>([]);
    let isLoading = $state(true);

    async function loadSessions() {
        isLoading = true;
        try {
            activeSessions = await listActiveSessions();
        } catch (e) {
            console.error("Error loading active sessions", e);
            toast("Error al cargar sesiones activas", "error");
        } finally {
            isLoading = false;
        }
    }

    onMount(() => {
        loadSessions();
        const interval = setInterval(loadSessions, 30000); // Refrescar cada 30s
        return () => clearInterval(interval);
    });

    function getTotalBalance(shift: ShiftInfo) {
        return shift.expected_cash + shift.expected_card + shift.expected_transfer;
    }
</script>

<div class="p-6 lg:p-10 max-w-7xl mx-auto w-full space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
    <!-- Header -->
    <header class="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
            <h1 class="text-4xl font-black tracking-tight text-base-content uppercase">
                Monitor de <span class="text-primary">Cajas Activas</span>
            </h1>
            <p class="text-base-content/60 font-medium mt-1">Supervisión en tiempo real de todos los puntos de venta abiertos</p>
        </div>

        <Button variant="ghost" class="font-bold gap-2" onclick={loadSessions} disabled={isLoading}>
            {#if isLoading}
                <span class="loading loading-spinner loading-xs"></span>
            {:else}
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
            {/if}
            Actualizar
        </Button>
    </header>

    {#if isLoading && activeSessions.length === 0}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {#each Array(3) as _}
                <div class="h-64 bg-base-300 animate-pulse rounded-[2.5rem]"></div>
            {/each}
        </div>
    {:else if activeSessions.length === 0}
        <div class="bg-base-100 rounded-[3rem] border-2 border-dashed border-base-300 p-20 text-center space-y-4">
            <div class="w-24 h-24 bg-base-200 rounded-full flex items-center justify-center mx-auto text-base-content/20">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-12 h-12">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
            </div>
            <h2 class="text-2xl font-black tracking-tight">No hay cajas abiertas</h2>
            <p class="text-base-content/50 max-w-md mx-auto font-medium text-sm">En este momento no hay ningún usuario operando un turno de venta.</p>
        </div>
    {:else}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {#each activeSessions as session}
                <div class="card bg-base-100 shadow-xl border border-base-200 rounded-[2.5rem] overflow-hidden group hover:shadow-2xl hover:shadow-primary/10 transition-all duration-500">
                    <div class="card-body p-8">
                        <!-- User & Register Info -->
                        <div class="flex justify-between items-start mb-6">
                            <div class="flex items-center gap-4">
                                <div class="w-12 h-12 bg-primary/10 text-primary rounded-2xl flex items-center justify-center font-black text-xl">
                                    {session.register_id}
                                </div>
                                <div>
                                    <h3 class="font-black text-lg text-base-content group-hover:text-primary transition-colors">Cajero #{session.user_id ? session.user_id.toString().substring(0,4) : '??'}</h3>
                                    <p class="text-[10px] font-black uppercase tracking-widest opacity-40">Caja Registradora {session.register_id}</p>
                                </div>
                            </div>
                            <div class="badge badge-success font-black text-[10px] p-3 animate-pulse">EN VIVO</div>
                        </div>

                        <!-- Balance Grid -->
                        <div class="grid grid-cols-2 gap-4 mb-8">
                            <div class="bg-base-200/50 p-4 rounded-2xl">
                                <span class="text-[9px] font-black uppercase tracking-widest opacity-40 block mb-1">Efectivo</span>
                                <span class="text-lg font-black tabular-nums">{formatCurrency(session.expected_cash)}</span>
                            </div>
                            <div class="bg-base-200/50 p-4 rounded-2xl">
                                <span class="text-[9px] font-black uppercase tracking-widest opacity-40 block mb-1">Tarjetas</span>
                                <span class="text-lg font-black tabular-nums">{formatCurrency(session.expected_card)}</span>
                            </div>
                        </div>

                        <!-- Total Footer -->
                        <div class="flex items-end justify-between border-t border-base-200 pt-6 mt-auto">
                            <div>
                                <span class="text-[9px] font-black uppercase tracking-widest opacity-40 block">Venta Total</span>
                                <span class="text-2xl font-black text-primary tabular-nums tracking-tighter">{formatCurrency(getTotalBalance(session))}</span>
                            </div>
                            <div class="text-right">
                                <span class="text-[9px] font-black uppercase tracking-widest opacity-40 block">Abierto desde</span>
                                <span class="text-[10px] font-bold">{new Date(session.start_time).toLocaleTimeString()}</span>
                            </div>
                        </div>

                        <!-- Actions -->
                        <div class="mt-6">
                            <Button variant="ghost" class="w-full font-black uppercase text-xs tracking-widest rounded-2xl py-6" onclick={() => window.location.href = `/admin/shifts/${session.id}`}>
                                Ver Auditoría Detallada
                            </Button>
                        </div>
                    </div>
                </div>
            {/each}
        </div>
    {/if}
</div>
