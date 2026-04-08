<script lang="ts">
    import { TableService, type Table } from '$lib/api/tables';

    let { isOpen, table = null, onClose, onSave } = $props<{
        isOpen: boolean;
        table?: Partial<Table> | null;
        onClose: () => void;
        onSave: () => void;
    }>();

    let formData = $state<Partial<Table>>({
        number: 0,
        capacity: 4,
        location: ''
    });

    let isSubmitting = $state(false);

    $effect(() => {
        if (isOpen) {
            if (table) {
                formData = { ...table };
            } else {
                formData = { number: 0, capacity: 4, location: '' };
            }
        }
    });

    async function handleSubmit(e: Event) {
        e.preventDefault();
        isSubmitting = true;
        try {
            if (table && table.id) {
                await TableService.update(table.id, formData);
            } else {
                await TableService.create(formData.number!, formData.capacity!, formData.location!);
            }
            onSave();
            onClose();
        } catch (error: any) {
            alert('Error al guardar la mesa: ' + error.message);
        } finally {
            isSubmitting = false;
        }
    }
</script>

<dialog class="modal {isOpen ? 'modal-open' : ''}">
    <div class="modal-box">
        <h3 class="font-bold text-lg mb-6">{table ? 'Editar Mesa' : 'Añadir Nueva Mesa'}</h3>
        
        <form onsubmit={handleSubmit} class="space-y-4">
            <div class="form-control">
                <label class="label" for="table_number"><span class="label-text font-bold">Número de Mesa</span></label>
                <input 
                    id="table_number"
                    type="number" 
                    bind:value={formData.number} 
                    class="input input-bordered w-full" 
                    required 
                    min="1"
                />
            </div>

            <div class="form-control">
                <label class="label" for="table_capacity"><span class="label-text font-bold">Capacidad (Personas)</span></label>
                <input 
                    id="table_capacity"
                    type="number" 
                    bind:value={formData.capacity} 
                    class="input input-bordered w-full" 
                    required 
                    min="1"
                />
            </div>

            <div class="form-control">
                <label class="label" for="table_location"><span class="label-text font-bold">Ubicación (Opcional)</span></label>
                <input 
                    id="table_location"
                    type="text" 
                    bind:value={formData.location} 
                    placeholder="Ej: Terraza, Planta Alta" 
                    class="input input-bordered w-full" 
                />
            </div>

            <div class="modal-action gap-2">
                <button type="button" class="btn btn-ghost" onclick={onClose}>Cancelar</button>
                <button type="submit" class="btn btn-primary px-8" disabled={isSubmitting}>
                    {#if isSubmitting}
                        <span class="loading loading-spinner loading-sm"></span>
                    {/if}
                    Guardar
                </button>
            </div>
        </form>
    </div>
    <form method="dialog" class="modal-backdrop bg-black/50">
        <button onclick={onClose}>close</button>
    </form>
</dialog>
