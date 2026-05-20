<script lang="ts">
    import { onMount } from 'svelte';
    import { posSocket } from '$lib/pos_socket.svelte';
    import { IoTService } from '$lib/api/iot';
    import Button from '$lib/components/ui/Button.svelte';
    import IoTManagementModal from '$lib/components/IoTManagementModal.svelte';
    import { toast } from '$lib/toast.svelte.js';
    import Toolbar from '$lib/components/ui/Toolbar.svelte';

    let showModal = $state(false);
    let selectedDevice = $state<any>(null);
    let isLoading = $state(true);

    onMount(async () => {
        posSocket.subscribe('admin_iot');
        try {
            // Cargar inicial
            const devices = await IoTService.listDevices();
            // Marcar todos como online si tienen una conexión activa reportada por websocket
            // En este punto, el websocket ya puede haber enviado algunos 'status'
            posSocket.iotDevices = devices;
        } catch (e) {
            toast.error("Error cargando dispositivos");
        } finally {
            isLoading = false;
        }
    });

    function openModal(device = null) {
        selectedDevice = device;
        showModal = true;
    }

    async function handleDelete(id: number) {
        if (!confirm("¿Eliminar este dispositivo permanentemente?")) return;
        try {
            await IoTService.deleteDevice(id);
            posSocket.iotDevices = posSocket.iotDevices.filter((d: any) => d.id !== id);
            toast.success("Dispositivo eliminado");
        } catch (e) {
            toast.error("Error al eliminar");
        }
    }

    async function handleSync() {
        try {
            const res = await IoTService.syncDevices();
            toast.success(res.message || "Sincronización enviada");
        } catch (e) {
            toast.error("Fallo al sincronizar");
        }
    }

    const onlineCount = $derived(posSocket.iotDevices.filter(d => d.is_online).length);
    const totalCount = $derived(posSocket.iotDevices.length);
</script>

<svelte:head>
    <title>Blackshot IoT | Gestión de Dispositivos</title>
</svelte:head>

<div class="p-4 lg:p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500 overflow-y-auto h-full">
    
    <!-- Unified Header Toolbar -->
    <Toolbar title="Gestión IoT">
        {#snippet left()}
            <a href="/admin" class="btn btn-ghost btn-sm font-black gap-1 rounded-xl uppercase tracking-wider text-xs">
                ← Volver
            </a>
            
            <div class="h-5 w-[1px] bg-base-300 mx-2 hidden sm:block"></div>
            
            <div class="hidden sm:flex items-center gap-4 text-xs font-bold text-base-content/60">
                <span>Total: <strong class="text-base-content font-black">{totalCount}</strong></span>
                <span class="flex items-center gap-1.5">
                    En línea: <strong class="text-success font-black">{onlineCount}</strong>
                    <span class="flex h-2 w-2 rounded-full bg-success animate-pulse"></span>
                </span>
            </div>
        {/snippet}
        
        {#snippet right()}
            <Button variant="outline" size="sm" class="px-4 font-black rounded-xl border-2 group text-xs font-bold" onclick={handleSync}>
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1.5 group-hover:rotate-180 transition-transform duration-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                SINCRONIZAR
            </Button>

            <Button variant="primary" size="sm" class="px-5 font-black rounded-xl shadow-md group text-xs font-bold" onclick={() => openModal()}>
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1.5 group-hover:rotate-90 transition-transform duration-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
                </svg>
                REGISTRAR
            </Button>
        {/snippet}
    </Toolbar>

    {#if isLoading}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {#each Array(3) as _}
                <div class="h-48 bg-base-100/50 rounded-3xl animate-pulse"></div>
            {/each}
        </div>
    {:else if posSocket.iotDevices.length === 0}
        <div class="flex flex-col items-center justify-center py-20 bg-base-100/30 rounded-[3rem] border-2 border-dashed border-base-content/10">
            <div class="w-24 h-24 bg-base-200 rounded-full flex items-center justify-center mb-6 text-base-content/20">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>
            </div>
            <p class="text-xl font-bold opacity-40">No hay dispositivos registrados</p>
            <Button variant="ghost" class="mt-4" onclick={() => openModal()}>Comenzar ahora</Button>
        </div>
    {:else}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-20">
            {#each posSocket.iotDevices as device}
                <div class="group relative bg-base-100 rounded-[2.5rem] p-8 border border-base-content/5 shadow-sm hover:shadow-2xl hover:-translate-y-2 transition-all duration-500 overflow-hidden">
                    <!-- Glass Background Effect -->
                    <div class="absolute -top-20 -right-20 w-64 h-64 bg-primary/5 rounded-full blur-3xl group-hover:bg-primary/10 transition-colors duration-700"></div>
                    
                    <div class="flex justify-between items-start mb-8 relative z-10">
                        <div class="flex items-center gap-4">
                            <div class="w-14 h-14 rounded-2xl bg-base-200 flex items-center justify-center text-3xl group-hover:scale-110 transition-transform duration-500 shadow-inner">
                                {#if device.type === 'esp32'} ⚡ 
                                {:else if device.type === 'esp8266'} 🔌
                                {:else} 📡 {/if}
                            </div>
                            <div>
                                <h3 class="font-black text-2xl tracking-tight leading-none mb-1 text-base-content group-hover:text-primary transition-colors">{device.name || 'Sin Nombre'}</h3>
                                <div class="flex items-center gap-2">
                                    <span class="text-[10px] font-mono opacity-40 uppercase tracking-widest">{device.device_id}</span>
                                </div>
                            </div>
                        </div>
                        <div class="flex flex-col items-end gap-2">
                            <div class="flex items-center gap-1.5 px-3 py-1 rounded-full {device.is_online ? 'bg-success/10 text-success' : 'bg-error/10 text-error'}">
                                <div class="w-1.5 h-1.5 rounded-full bg-current {device.is_online ? 'animate-pulse' : ''}"></div>
                                <span class="text-[10px] font-black tracking-widest uppercase">{device.is_online ? 'CONECTADO' : 'DESCONECTADO'}</span>
                            </div>
                            {#if device.table_id}
                                <span class="text-[10px] font-black tracking-widest border border-primary/20 text-primary px-3 py-1 rounded-full uppercase">Mesa {device.table_id}</span>
                            {/if}
                        </div>
                    </div>

                    <div class="flex items-center gap-8 mb-8 relative z-10 px-2">
                        <div class="flex-1">
                            <div class="flex justify-between items-end mb-2">
                                <span class="text-[10px] font-bold opacity-40 uppercase tracking-widest">Señal</span>
                                <span class="text-xs font-black {device.rssi > -60 ? 'text-success' : device.rssi > -80 ? 'text-warning' : 'text-error'}">
                                    {device.rssi || '--'} dBm
                                </span>
                            </div>
                            <div class="h-1.5 w-full bg-base-200 rounded-full overflow-hidden">
                                <div 
                                    class="h-full rounded-full transition-all duration-1000 {device.rssi > -60 ? 'bg-success shadow-[0_0_8px_#4ade80]' : device.rssi > -80 ? 'bg-warning shadow-[0_0_8px_#fbbf24]' : 'bg-error shadow-[0_0_8px_#f87171]'}" 
                                    style="width: {Math.max(0, Math.min(100, (device.rssi + 100) * 1.5))}%"
                                ></div>
                            </div>
                        </div>
                        
                        <div class="flex-1">
                            <div class="flex justify-between items-end mb-2">
                                <span class="text-[10px] font-bold opacity-40 uppercase tracking-widest">Batería</span>
                                <span class="text-xs font-black {device.battery_level > 20 ? 'text-base-content' : 'text-error'}">
                                    {device.battery_level !== null ? device.battery_level + '%' : '--'}
                                </span>
                            </div>
                            <div class="h-1.5 w-full bg-base-200 rounded-full overflow-hidden">
                                <div 
                                    class="h-full rounded-full transition-all duration-1000 {device.battery_level > 20 ? 'bg-primary' : 'bg-error'}" 
                                    style="width: {device.battery_level || 0}%"
                                ></div>
                            </div>
                        </div>
                    </div>

                    <div class="flex items-center justify-between gap-3 relative z-10">
                        <Button variant="outline" size="sm" class="flex-1 rounded-2xl font-bold py-5" onclick={() => openModal(device)}>
                            CONFIGURAR
                        </Button>
                        <button class="btn btn-ghost btn-sm btn-square rounded-2xl h-12 w-12 text-error/30 hover:text-error hover:bg-error/5 transition-colors" onclick={() => handleDelete(device.id)}>
                            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" viewBox="0 0 20 20" fill="currentColor">
                                <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                            </svg>
                        </button>
                    </div>
                    
                    {#if device.is_online}
                        <div class="absolute bottom-0 left-0 w-full h-1 bg-success/5">
                            <div class="h-full bg-success animate-progress w-full shadow-[0_0_15px_#4ade80]"></div>
                        </div>
                    {/if}
                </div>
            {/each}
        </div>
    {/if}
</div>

{#if showModal}
    <IoTManagementModal 
        device={selectedDevice} 
        onSave={() => { showModal = false; IoTService.listDevices().then(d => posSocket.iotDevices = d); }} 
        onClose={() => showModal = false} 
    />
{/if}

<style>
    @keyframes progress {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(100%); }
    }
    .animate-progress {
        animation: progress 2.5s infinite linear;
    }
</style>
