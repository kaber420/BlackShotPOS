<script lang="ts">
    import { onMount } from 'svelte';
    import { fetchApi } from '$lib/api';
    import Button from '$lib/components/ui/Button.svelte';
    import { appState, can } from '$lib/app_state.svelte';
    import { formatCurrency, formatDate, formatDateTime } from '$lib/utils';
    
    type Period = 'today' | 'week' | 'month';
    let period: Period = $state('today');
    let summary: any = $state(null);
    let recentShifts: any[] = $state([]);
    let loading = $state(true);

    onMount(async () => {
        await loadData();
    });

    async function loadData() {
        loading = true;
        try {
            const [summaryRes, shiftsRes] = await Promise.all([
                fetchApi(`/api/v1/pos/system/analytics/business-summary?period=${period}`),
                fetchApi('/api/v1/pos/sales/shifts/'),
            ]);
            summary = summaryRes;
            // Solo mostrar los últimos 5
            recentShifts = Array.isArray(shiftsRes) ? shiftsRes.slice(0, 5) : [];
        } catch (e) {
            console.error("Error al cargar datos del dashboard", e);
        } finally {
            loading = false;
        }
    }

    // Reactividad para recargar cuando cambie el período
    $effect(() => {
        if (period) {
            loadData();
        }
    });

    const quickLinks = [
        { 
            name: 'Realizar Corte', 
            href: '/accounting', 
            icon: '💵', 
            desc: 'Gestión de caja y turno actual',
            show: can.manageShifts()
        },
        { 
            name: 'Historial de Cortes', 
            href: '/accounting', 
            icon: '📋', 
            desc: 'Auditoría de turnos pasados',
            show: can.viewReports()
        },
        { 
            name: 'Analíticas', 
            href: '/admin/analytics', 
            icon: '📈', 
            desc: 'Reportes de ventas detallados',
            show: can.viewReports()
        },
        { 
            name: 'Usuarios', 
            href: '/admin/users', 
            icon: '👥', 
            desc: 'Gestión de personal y accesos',
            show: can.manageUsers()
        },
        { 
            name: 'Estaciones de Producción', 
            href: '/admin/config/stations', 
            icon: '🍳', 
            desc: 'Configuración de áreas de preparación',
            show: can.manageMenu()
        },
        { 
            name: 'Bitácora / Auditoría', 
            href: '/admin/audits', 
            icon: '🛡️', 
            desc: 'Registro global de eventos operativos',
            show: can.viewReports()
        }
    ].filter(link => link.show);

</script>

<div class="p-6 lg:p-10 max-w-7xl mx-auto w-full space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
    
    <!-- Header -->
    <header class="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
            <h1 class="text-4xl font-black tracking-tight text-base-content uppercase">
                Panel de <span class="text-primary">Administración</span>
            </h1>
            <p class="text-base-content/60 font-medium mt-1">Gestión centralizada de operaciones y reportes de negocio</p>
        </div>

        <div class="tabs tabs-boxed bg-base-300 p-1 rounded-2xl shadow-inner">
            <button 
                class="tab rounded-xl font-bold transition-all duration-200 {period === 'today' ? 'tab-active bg-primary text-primary-content shadow-lg' : ''}" 
                onclick={() => period = 'today'}>Hoy</button>
            <button 
                class="tab rounded-xl font-bold transition-all duration-200 {period === 'week' ? 'tab-active bg-primary text-primary-content shadow-lg' : ''}" 
                onclick={() => period = 'week'}>Semana</button>
            <button 
                class="tab rounded-xl font-bold transition-all duration-200 {period === 'month' ? 'tab-active bg-primary text-primary-content shadow-lg' : ''}" 
                onclick={() => period = 'month'}>Mes</button>
        </div>
    </header>

    {#if loading && !summary}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {#each Array(4) as _}
                <div class="h-32 bg-base-300 animate-pulse rounded-3xl"></div>
            {/each}
        </div>
        <div class="h-64 bg-base-300 animate-pulse rounded-3xl"></div>
    {:else if summary}
        <!-- KPI Cards -->
        <section class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div class="card bg-base-100 shadow-xl border border-success/10 overflow-hidden group hover:shadow-success/5 transition-all duration-300">
                <div class="card-body p-6">
                    <div class="flex justify-between items-start">
                        <div class="p-3 bg-success/10 rounded-2xl text-success">
                            <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </div>
                        <span class="text-xs font-black uppercase tracking-widest text-success/50">Ventas ({period})</span>
                    </div>
                    <div class="mt-4">
                        <h2 class="text-3xl font-black text-base-content tabular-nums">{formatCurrency(summary.total_sales)}</h2>
                        <p class="text-sm font-bold text-success/60 mt-1">{summary.total_payments} cobros realizados</p>
                    </div>
                </div>
            </div>

            <div class="card bg-base-100 shadow-xl border border-info/10 overflow-hidden group hover:shadow-info/5 transition-all duration-300">
                <div class="card-body p-6">
                    <div class="flex justify-between items-start">
                        <div class="p-3 bg-info/10 rounded-2xl text-info">
                            <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                            </svg>
                        </div>
                        <span class="text-xs font-black uppercase tracking-widest text-info/50">Órdenes</span>
                    </div>
                    <div class="mt-4">
                        <h2 class="text-3xl font-black text-base-content tabular-nums">{summary.total_orders}</h2>
                        <p class="text-sm font-bold text-info/60 mt-1">Total de tickets creados</p>
                    </div>
                </div>
            </div>

            <div class="card bg-base-100 shadow-xl border border-secondary/10 overflow-hidden group hover:shadow-secondary/5 transition-all duration-300">
                <div class="card-body p-6">
                    <div class="flex justify-between items-start">
                        <div class="p-3 bg-secondary/10 rounded-2xl text-secondary">
                            <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </div>
                        <span class="text-xs font-black uppercase tracking-widest text-secondary/50">Cortes Cerrados</span>
                    </div>
                    <div class="mt-4">
                        <h2 class="text-3xl font-black text-base-content tabular-nums">{summary.closed_shifts_count}</h2>
                        <p class="text-sm font-bold text-secondary/60 mt-1">Turnos de caja completados</p>
                    </div>
                </div>
            </div>

            <div class="card bg-base-100 shadow-xl border border-error/10 overflow-hidden group hover:shadow-error/5 transition-all duration-300">
                <div class="card-body p-6">
                    <div class="flex justify-between items-start">
                        <div class="p-3 bg-error/10 rounded-2xl text-error">
                            <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </div>
                        <span class="text-xs font-black uppercase tracking-widest text-error/50">Cancelaciones</span>
                    </div>
                    <div class="mt-4">
                        <h2 class="text-3xl font-black text-base-content tabular-nums">{summary.orders_by_status.CANCELLED || 0}</h2>
                        <p class="text-sm font-bold text-error/60 mt-1">Órdenes no concretadas</p>
                    </div>
                </div>
            </div>
        </section>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <!-- Quick Links -->
            <section class="lg:col-span-1 space-y-4">
                <h3 class="text-xl font-black uppercase tracking-tight flex items-center gap-2">
                    <span class="w-1.5 h-6 bg-primary rounded-full"></span>
                    Accesos Rápidos
                </h3>
                <div class="grid grid-cols-1 gap-4">
                    {#each quickLinks as link}
                        <a 
                            href={link.href} 
                            class="flex items-center gap-4 p-4 bg-base-100 hover:bg-base-300 border border-base-content/5 rounded-2xl shadow-sm transition-all duration-200 group active:scale-95"
                        >
                            <div class="w-12 h-12 flex items-center justify-center bg-base-200 rounded-xl text-2xl group-hover:scale-110 transition-transform">
                                {link.icon}
                            </div>
                            <div>
                                <h4 class="font-black text-base-content">{link.name}</h4>
                                <p class="text-xs font-medium text-base-content/50">{link.desc}</p>
                            </div>
                            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 ml-auto text-base-content/20 group-hover:text-primary transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M9 5l7 7-7 7" />
                            </svg>
                        </a>
                    {/each}
                </div>
            </section>

            <!-- Recent Shifts Preview -->
            <section class="lg:col-span-2 space-y-4">
                <div class="flex items-center justify-between">
                    <h3 class="text-xl font-black uppercase tracking-tight flex items-center gap-2">
                        <span class="w-1.5 h-6 bg-secondary rounded-full"></span>
                        Últimos Cortes de Caja
                    </h3>
                    <a href="/admin/shifts" class="btn btn-ghost btn-sm text-primary font-bold">Ver Todo</a>
                </div>
                
                <div class="bg-base-100 border border-base-content/5 rounded-3xl overflow-hidden shadow-xl">
                    <div class="overflow-x-auto">
                        <table class="table table-lg">
                            <thead>
                                <tr class="bg-base-200/50">
                                    <th class="font-black text-xs uppercase tracking-widest">ID</th>
                                    <th class="font-black text-xs uppercase tracking-widest">Fecha / Hora</th>
                                    <th class="font-black text-xs uppercase tracking-widest text-right">Ventas</th>
                                    <th class="font-black text-xs uppercase tracking-widest text-center">Diferencia</th>
                                    <th class="font-black text-xs uppercase tracking-widest">Estado</th>
                                </tr>
                            </thead>
                            <tbody>
                                {#if recentShifts.length === 0}
                                    <tr>
                                        <td colspan="5" class="text-center py-10 opacity-50 font-medium">No hay turnos registrados aún.</td>
                                    </tr>
                                {:else}
                                    {#each recentShifts as shift}
                                        <tr 
                                            class="hover:bg-base-200/30 transition-colors cursor-pointer" 
                                            onclick={() => window.location.href = `/admin/shifts/${shift.id}`}
                                        >
                                            <td class="font-black text-primary">#{shift.id}</td>
                                            <td>
                                                <div class="font-black text-sm">{formatDate(shift.start_time)}</div>
                                                <div class="text-[10px] opacity-50 uppercase font-black">{formatDateTime(shift.start_time).split(',')[1]}</div>
                                            </td>
                                            <td class="text-right font-black tabular-nums">{formatCurrency(shift.sales.total)}</td>
                                            <td class="text-center font-bold">
                                                {#if shift.status === 'CLOSED'}
                                                    <span class={shift.difference === 0 ? 'text-success' : shift.difference > 0 ? 'text-info' : 'text-error'}>
                                                        {shift.difference > 0 ? '+' : ''}{formatCurrency(shift.difference)}
                                                    </span>
                                                {:else}
                                                    <span class="opacity-30">—</span>
                                                {/if}
                                            </td>
                                            <td>
                                                {#if shift.status === 'OPEN'}
                                                    <div class="badge badge-warning badge-sm font-black gap-1 p-3">
                                                        <span class="w-1.5 h-1.5 bg-yellow-600 rounded-full animate-pulse"></span>
                                                        ABIERTO
                                                    </div>
                                                {:else}
                                                    <div class="badge badge-success badge-sm font-black gap-1 p-3">
                                                        <svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3" viewBox="0 0 20 20" fill="currentColor">
                                                            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                                                        </svg>
                                                        CERRADO
                                                    </div>
                                                {/if}
                                            </td>
                                        </tr>
                                    {/each}
                                {/if}
                            </tbody>
                        </table>
                    </div>
                </div>
            </section>
        </div>
    {/if}
</div>

<style>
    .tab-active {
        color: var(--pc);
    }
</style>
