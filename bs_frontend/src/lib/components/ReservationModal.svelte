<script lang="ts">
    import { ReservationService, TableService, type Reservation, type Table } from '$lib/api/tables';
    import Button from '$lib/components/ui/Button.svelte';
    import { addToast } from '$lib/toast.svelte.js';

    let { isOpen, reservation = null, initialTableId = null, onClose, onSave } = $props<{
        isOpen: boolean;
        reservation?: Partial<Reservation> | null;
        initialTableId?: number | null;
        onClose: () => void;
        onSave: () => void;
    }>();

    let formData = $state<Partial<Reservation>>({
        customer_name: '',
        customer_phone: '',
        table_id: undefined,
        pax: 2,
        reservation_time: '',
        notes: ''
    });

    let tables = $state<Table[]>([]);
    let isLoading = $state(false);

    $effect(() => {
        if (isOpen) {
            if (reservation) {
                formData = { ...reservation };
                // Format date for datetime-local input (YYYY-MM-DDThh:mm)
                if (formData.reservation_time) {
                   const date = new Date(formData.reservation_time);
                   // Adjust to local time for input
                   const tzOffset = date.getTimezoneOffset() * 60000;
                   const localISOTime = new Date(date.getTime() - tzOffset).toISOString().slice(0, 16);
                   formData.reservation_time = localISOTime;
                }
            } else {
                const now = new Date();
                const defaultTime = new Date(now.getTime() + 3600000); // 1 hour from now
                const tzOffset = defaultTime.getTimezoneOffset() * 60000;
                const localISOTime = new Date(defaultTime.getTime() - tzOffset).toISOString().slice(0, 16);
                
                formData = { 
                    customer_name: '', 
                    customer_phone: '', 
                    table_id: initialTableId || undefined, 
                    pax: 2, 
                    reservation_time: localISOTime,
                    notes: '' 
                };
            }
            loadTables();
        }
    });

    async function loadTables() {
        try {
            tables = await TableService.getAll();
        } catch (e) {
            console.error('Error loading tables', e);
        }
    }

    async function handleSubmit(e: Event) {
        e.preventDefault();
        isLoading = true;
        try {
            const payload = { ...formData };
            if (payload.reservation_time) {
                payload.reservation_time = new Date(payload.reservation_time).toISOString();
            }

            if (reservation && reservation.id) {
                // Update logic if needed
                addToast('Actualización parcial no soportada aún', 'info');
            } else {
                await ReservationService.create(payload);
                addToast('Reservación creada exitosamente', 'success');
            }
            onSave();
            onClose();
        } catch (error: any) {
            addToast('Error: ' + (error.detail || error.message), 'error');
        } finally {
            isLoading = false;
        }
    }
</script>

<dialog class="modal {isOpen ? 'modal-open' : ''}">
    <div class="modal-box max-w-md bg-base-100 rounded-[2rem] shadow-2xl border border-base-200">
        <div class="flex items-center justify-between mb-6">
            <h3 class="font-black text-2xl uppercase tracking-tighter text-primary">
                {reservation ? 'Editar' : 'Nueva'} <span class="text-base-content">Reserva</span>
            </h3>
            <Button variant="ghost" circle size="sm" onclick={onClose}>
                <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
            </Button>
        </div>
        
        <form onsubmit={handleSubmit} class="space-y-5">
            <div class="form-control">
                <label class="label py-1" for="res_name"><span class="label-text font-black uppercase text-[10px] tracking-widest opacity-50">Cliente</span></label>
                <input 
                    id="res_name"
                    type="text" 
                    bind:value={formData.customer_name} 
                    placeholder="Nombre completo"
                    class="input input-bordered w-full rounded-xl font-bold focus:ring-2 focus:ring-primary/20 transition-all" 
                    required 
                />
            </div>

            <div class="grid grid-cols-2 gap-4">
                <div class="form-control">
                    <label class="label py-1" for="res_phone"><span class="label-text font-black uppercase text-[10px] tracking-widest opacity-50">Teléfono</span></label>
                    <input 
                        id="res_phone"
                        type="tel" 
                        bind:value={formData.customer_phone} 
                        placeholder="10 dígitos"
                        class="input input-bordered w-full rounded-xl font-bold focus:ring-2 focus:ring-primary/20 transition-all" 
                    />
                </div>
                <div class="form-control">
                    <label class="label py-1" for="res_pax"><span class="label-text font-black uppercase text-[10px] tracking-widest opacity-50">Personas</span></label>
                    <input 
                        id="res_pax"
                        type="number" 
                        bind:value={formData.pax} 
                        class="input input-bordered w-full rounded-xl font-bold focus:ring-2 focus:ring-primary/20 transition-all" 
                        min="1"
                        required
                    />
                </div>
            </div>

            <div class="form-control">
                <label class="label py-1" for="res_time"><span class="label-text font-black uppercase text-[10px] tracking-widest opacity-50">Fecha y Hora</span></label>
                <input 
                    id="res_time"
                    type="datetime-local" 
                    bind:value={formData.reservation_time} 
                    class="input input-bordered w-full rounded-xl font-bold focus:ring-2 focus:ring-primary/20 transition-all" 
                    required
                />
            </div>

            <div class="form-control">
                <label class="label py-1" for="res_table"><span class="label-text font-black uppercase text-[10px] tracking-widest opacity-50">Mesa Asignada</span></label>
                <select id="res_table" bind:value={formData.table_id} class="select select-bordered w-full rounded-xl font-bold focus:ring-2 focus:ring-primary/20 transition-all">
                    <option value={undefined}>Seleccionar después...</option>
                    {#each tables as table}
                        <option value={table.id}>Mesa {table.number} — {table.location || 'Área General'} (Cap: {table.capacity})</option>
                    {/each}
                </select>
            </div>

            <div class="form-control">
                <label class="label py-1" for="res_notes"><span class="label-text font-black uppercase text-[10px] tracking-widest opacity-50">Notas / Comentarios</span></label>
                <textarea 
                    id="res_notes"
                    bind:value={formData.notes} 
                    class="textarea textarea-bordered w-full rounded-xl font-medium focus:ring-2 focus:ring-primary/20 transition-all" 
                    placeholder="Ej: Cumpleaños, alergias, mesa en ventana..."
                    rows="2"
                ></textarea>
            </div>

            <div class="modal-action mt-8">
                <Button type="submit" variant="primary" class="btn-block h-14 rounded-2xl font-black text-lg shadow-xl shadow-primary/20" {isLoading}>
                    Confirmar Reservación
                </Button>
            </div>
        </form>
    </div>
    <form method="dialog" class="modal-backdrop bg-black/60 backdrop-blur-sm">
        <button onclick={onClose}>close</button>
    </form>
</dialog>
