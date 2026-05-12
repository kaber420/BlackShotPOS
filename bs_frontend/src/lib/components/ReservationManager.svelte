<script lang="ts">
    import { onMount } from 'svelte';
    import { ReservationService, type Reservation, type ReservationStatus } from '$lib/api/tables';
    import Button from '$lib/components/ui/Button.svelte';
    import { formatDateTime } from '$lib/utils';
    import { addToast } from '$lib/toast.svelte.js';
    import ReservationModal from './ReservationModal.svelte';

    let { compact = false } = $props<{ compact?: boolean }>();

    let reservations = $state<Reservation[]>([]);
    let isLoading = $state(true);
    let showModal = $state(false);
    let selectedReservation = $state<Reservation | null>(null);

    onMount(async () => {
        await loadReservations();
    });

    async function loadReservations() {
        isLoading = true;
        try {
            // Cargar reservaciones de hoy en adelante
            const now = new Date();
            now.setHours(0, 0, 0, 0);
            reservations = await ReservationService.list(now.toISOString());
        } catch (e) {
            console.error('Error loading reservations', e);
        } finally {
            isLoading = false;
        }
    }

    async function handleStatusChange(id: number, status: ReservationStatus) {
        try {
            await ReservationService.updateStatus(id, status);
            addToast(`Estado actualizado a ${status}`, 'success');
            await loadReservations();
        } catch (e: any) {
            addToast('Error: ' + e.message, 'error');
        }
    }

    async function handleCheckIn(id: number) {
        try {
            await ReservationService.checkIn(id);
            addToast('Check-in exitoso. Orden creada.', 'success');
            await loadReservations();
        } catch (e: any) {
            addToast('Error: ' + (e.detail || e.message), 'error');
        }
    }

    function getStatusBadgeClass(status: ReservationStatus) {
        switch (status) {
            case 'PENDING': return 'badge-warning';
            case 'CONFIRMED': return 'badge-info';
            case 'COMPLETED': return 'badge-success';
            case 'CANCELLED': return 'badge-error';
            case 'NO_SHOW': return 'badge-ghost opacity-50';
            default: return '';
        }
    }
</script>

<div class="space-y-6 {compact ? 'space-y-4' : ''}">
    <div class="flex items-center justify-between">
        <h3 class="{compact ? 'text-lg' : 'text-2xl'} font-black uppercase tracking-tighter flex items-center gap-2">
            <span class="w-1.5 h-6 bg-primary rounded-full"></span>
            {compact ? 'Reservas' : 'Agenda de Reservaciones'}
        </h3>
        <Button variant="primary" size="xs" class="rounded-lg font-bold" onclick={() => { selectedReservation = null; showModal = true; }}>
            {compact ? '+' : 'Nueva'}
        </Button>
    </div>

    <div class="bg-base-100 {compact ? 'border-none shadow-none' : 'border border-base-content/5 shadow-xl'} rounded-3xl overflow-hidden min-h-[100px]">
        {#if isLoading}
            <div class="flex items-center justify-center py-10">
                <span class="loading loading-spinner loading-md text-primary"></span>
            </div>
        {:else if reservations.length === 0}
            <div class="flex flex-col items-center justify-center py-10 opacity-50 space-y-2">
                <div class="{compact ? 'text-2xl' : 'text-6xl'}">📅</div>
                <p class="font-black uppercase tracking-widest text-[10px]">Sin reservas</p>
            </div>
        {:else if compact}
            <!-- Compact List for Sidebar -->
            <div class="flex flex-col gap-2">
                {#each reservations as res}
                    <div class="p-3 bg-base-200/50 rounded-2xl border border-base-content/5 hover:bg-base-200 transition-colors group">
                        <div class="flex justify-between items-start mb-1">
                            <span class="text-[10px] font-black uppercase text-primary">{formatDateTime(res.reservation_time).split(',')[1]}</span>
                            <div class="badge {getStatusBadgeClass(res.status)} font-black text-[8px] px-1 h-4">
                                {res.status}
                            </div>
                        </div>
                        <div class="font-black text-sm truncate">{res.customer_name}</div>
                        <div class="flex items-center justify-between mt-2">
                            <span class="text-[9px] font-bold opacity-50">Mesa {res.table_id || '?'} • {res.pax}p</span>
                            <div class="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                {#if res.status === 'PENDING' || res.status === 'CONFIRMED'}
                                    <button class="btn btn-xs btn-success btn-circle h-6 w-6 min-h-0" onclick={() => handleCheckIn(res.id)} title="Check-in">
                                        <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" /></svg>
                                    </button>
                                {/if}
                            </div>
                        </div>
                    </div>
                {/each}
            </div>
        {:else}
            <div class="overflow-x-auto">
                <table class="table table-lg">
                    <thead>
                        <tr class="bg-base-200/50">
                            <th class="font-black text-xs uppercase tracking-widest">Hora</th>
                            <th class="font-black text-xs uppercase tracking-widest">Cliente</th>
                            <th class="font-black text-xs uppercase tracking-widest">Mesa / Pax</th>
                            <th class="font-black text-xs uppercase tracking-widest">Estado</th>
                            <th class="font-black text-xs uppercase tracking-widest text-right">Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each reservations as res}
                            <tr class="hover:bg-base-200/30 transition-colors">
                                <td>
                                    <div class="font-black text-sm">{formatDateTime(res.reservation_time).split(',')[1]}</div>
                                    <div class="text-[10px] opacity-50 font-bold uppercase">{formatDateTime(res.reservation_time).split(',')[0]}</div>
                                </td>
                                <td>
                                    <div class="font-black text-base-content">{res.customer_name}</div>
                                    <div class="text-xs opacity-50 font-medium">{res.customer_phone || 'Sin teléfono'}</div>
                                </td>
                                <td>
                                    <div class="flex items-center gap-2">
                                        <div class="badge badge-outline font-black">Mesa {res.table_id || '?'}</div>
                                        <div class="badge badge-ghost font-bold">{res.pax} pax</div>
                                    </div>
                                </td>
                                <td>
                                    <div class="badge {getStatusBadgeClass(res.status)} font-black text-[10px] p-2">
                                        {res.status}
                                    </div>
                                </td>
                                <td class="text-right space-x-1">
                                    {#if res.status === 'PENDING' || res.status === 'CONFIRMED'}
                                        <Button variant="success" size="xs" class="font-black rounded-lg" onclick={() => handleCheckIn(res.id)}>
                                            Check-in
                                        </Button>
                                        {#if res.status === 'PENDING'}
                                            <Button variant="info" size="xs" class="font-black rounded-lg" onclick={() => handleStatusChange(res.id, 'CONFIRMED')}>
                                                Confirmar
                                            </Button>
                                        {/if}
                                        <Button variant="danger" size="xs" class="font-black rounded-lg" onclick={() => handleStatusChange(res.id, 'CANCELLED')}>
                                            X
                                        </Button>
                                    {/if}
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            </div>
        {/if}
    </div>
</div>

<ReservationModal 
    isOpen={showModal} 
    reservation={selectedReservation} 
    onClose={() => showModal = false} 
    onSave={loadReservations} 
/>
