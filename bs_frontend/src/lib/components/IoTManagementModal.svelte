<script lang="ts">
    import { IoTService } from '$lib/api/iot';
    import { TableService } from '$lib/api/tables';
    import Button from './ui/Button.svelte';
    import { onMount } from 'svelte';
    import { toast } from '$lib/toast.svelte.js';

    let { device = null, onSave, onClose } = $props();

    let name = $state(device?.name || '');
    let device_id = $state(device?.device_id || '');
    let type = $state(device?.type || 'esp32');
    let table_id = $state(device?.table_id || null);
    let is_active = $state(device?.is_active !== false);
    
    let tables = $state<any[]>([]);
    let isLoading = $state(false);
    let isSaving = $state(false);
    let generatedToken = $state('');

    onMount(async () => {
        try {
            tables = await TableService.getAll();
        } catch (e) {
            console.error("Error cargando mesas", e);
        }
    });

    async function handleSave() {
        isSaving = true;
        try {
            const payload = { name, device_id, type, table_id, is_active };
            if (device) {
                await IoTService.updateDevice(device.id, payload);
                toast.success("Dispositivo actualizado");
            } else {
                const newDevice = await IoTService.createDevice(payload);
                generatedToken = newDevice.token;
                toast.success("Dispositivo registrado");
            }
            if (!generatedToken) {
                onSave();
            }
        } catch (e) {
            toast.error("Error al guardar: " + e);
        } finally {
            isSaving = false;
        }
    }

    async function handleRotateToken() {
        if (!confirm("¿Estás seguro? El dispositivo actual se desconectará hasta que actualices el token.")) return;
        try {
            const res = await IoTService.rotateToken(device.id);
            generatedToken = res.token;
            toast.success("Token rotado con éxito");
        } catch (e) {
            toast.error("Error al rotar token: " + e);
        }
    }
</script>

<div class="modal modal-open bg-base-300/60 backdrop-blur-sm z-50">
    <div class="modal-box max-w-lg border border-base-content/10 shadow-2xl">
        <h3 class="font-black text-2xl mb-6 flex items-center gap-2">
            <span class="text-primary">{device ? '⚙️ Editar' : '🔌 Nuevo'}</span> Dispositivo IoT
        </h3>

        {#if generatedToken}
            <div class="bg-success/10 border border-success/30 p-6 rounded-2xl mb-6 animate-in fade-in zoom-in duration-300">
                <p class="text-success font-bold mb-2 flex items-center gap-2">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                    </svg>
                    Token Generado con Éxito
                </p>
                <p class="text-xs opacity-70 mb-4">Copia este token ahora. Por seguridad, no se volverá a mostrar completo.</p>
                <div class="bg-base-300 p-4 rounded-xl font-mono text-sm break-all border border-base-content/10 select-all">
                    {generatedToken}
                </div>
                <div class="mt-6">
                    <Button variant="success" class="btn-block" onclick={onSave}>Entendido, guardado</Button>
                </div>
            </div>
        {:else}
            <div class="space-y-5">
                <div class="form-control">
                    <label class="label"><span class="label-text font-bold">Hardware ID (MAC/UUID)</span></label>
                    <input type="text" bind:value={device_id} placeholder="ej: AA:BB:CC:11:22:33" class="input input-bordered font-mono" disabled={!!device} />
                </div>

                <div class="form-control">
                    <label class="label"><span class="label-text font-bold">Nombre / Alias</span></label>
                    <input type="text" bind:value={name} placeholder="ej: Pantalla Mesa 5" class="input input-bordered" />
                </div>

                <div class="grid grid-cols-2 gap-4">
                    <div class="form-control">
                        <label class="label"><span class="label-text font-bold">Tipo</span></label>
                        <select bind:value={type} class="select select-bordered">
                            <option value="esp32">ESP32 (Standard)</option>
                            <option value="esp8266">ESP8266 (Legacy)</option>
                            <option value="sensor">Sensor / Otros</option>
                        </select>
                    </div>

                    <div class="form-control">
                        <label class="label"><span class="label-text font-bold">Vincular a Mesa</span></label>
                        <select bind:value={table_id} class="select select-bordered text-base">
                            <option value={null}>Ninguna (Desvinculado)</option>
                            {#each tables as table}
                                <option value={table.id}>Mesa {table.number}</option>
                            {/each}
                        </select>
                    </div>
                </div>

                {#if device}
                    <div class="divider">Seguridad</div>
                    <div class="flex items-center justify-between p-4 bg-warning/5 border border-warning/20 rounded-xl">
                        <div>
                            <p class="font-bold text-sm">Rotación de Seguridad</p>
                            <p class="text-xs opacity-60">Invalida el token actual y genera uno nuevo.</p>
                        </div>
                        <Button variant="warning" size="sm" onclick={handleRotateToken}>Rotar Token</Button>
                    </div>
                {/if}
            </div>

            <div class="modal-action mt-8 flex gap-3">
                <Button variant="ghost" onclick={onClose} disabled={isSaving}>Cancelar</Button>
                <Button variant="primary" onclick={handleSave} isLoading={isSaving} class="px-8">
                    {device ? 'Guardar Cambios' : 'Registrar Dispositivo'}
                </Button>
            </div>
        {/if}
    </div>
</div>
