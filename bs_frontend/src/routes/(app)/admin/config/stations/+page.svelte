<script lang="ts">
    /**
     * Blackshot POS - Production Stations Management Page
     * -----------------------------------------------------
     * Dedicated view for managing where products are prepared.
     */
    import { onMount } from 'svelte';
    import { ProductionAreaService, type ProductionArea } from '$lib/api/production_areas';
    import { addToast } from '$lib/toast.svelte.js';
    import Button from '$lib/components/ui/Button.svelte';
    import ProductionAreaModal from '$lib/components/ProductionAreaModal.svelte';

    let areas = $state<ProductionArea[]>([]);
    let isLoading = $state(true);
    let isModalOpen = $state(false);
    let areaToEdit = $state<ProductionArea | null>(null);

    async function loadData() {
        isLoading = true;
        try {
            areas = await ProductionAreaService.getAll();
        } catch (e) {
            addToast("Error al cargar estaciones", "error");
        } finally {
            isLoading = false;
        }
    }

    function openCreate() {
        areaToEdit = null;
        isModalOpen = true;
    }

    onMount(loadData);
</script>

<div class="p-6 lg:p-10 max-w-6xl mx-auto flex-1 min-h-0 overflow-y-auto w-full space-y-8 animate-in fade-in slide-in-from-bottom-4">
    
    <!-- Header -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div class="flex flex-col gap-1">
            <h1 class="text-4xl font-black tracking-tight flex items-center gap-3 uppercase">
                <div class="w-12 h-12 bg-orange-500 rounded-2xl flex items-center justify-center text-white shadow-lg shadow-orange-500/20">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-7 h-7">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5m-9-6h.008v.008H12v-.008zM12 15h.008v.008H12V15zm0 2.25h.008v.008H12v-.008zM9.75 15h.008v.008H9.75V15zm0 2.25h.008v.008H9.75v-.008zM7.5 15h.008v.008H7.5V15zm0 2.25h.008v.008H7.5v-.008zm6.75-4.5h.008v.008h-.008v-.008zm0 2.25h.008v.008h-.008V15zm0 2.25h.008v.008h-.008v-.008zm2.25-4.5h.008v.008H16.5v-.008zm0 2.25h.008v.008H16.5V15z" />
                    </svg>
                </div>
                Zonas de Producción
            </h1>
            <p class="text-base-content/60 font-medium ml-1">Configura tus áreas de trabajo e impresoras de comandas.</p>
        </div>
        
        <div class="flex gap-2">
            <a href="/admin/config" class="btn btn-ghost gap-2 font-bold uppercase text-xs">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-4 h-4"><path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" /></svg>
                Volver al Hub
            </a>
            <Button variant="primary" class="font-black uppercase tracking-widest text-xs px-6" onclick={openCreate}>
                Nueva Zona
            </Button>
        </div>
    </div>

    <!-- Grid Layout for Areas -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {#if isLoading}
            {#each Array(6) as _}
                <div class="h-48 bg-base-100 animate-pulse rounded-[2rem] border border-base-200"></div>
            {/each}
        {:else if areas.length === 0}
            <div class="col-span-full py-20 text-center bg-base-100 rounded-[3rem] border-2 border-dashed border-base-200">
                <p class="opacity-50 font-medium">No hay zonas configuradas aún.</p>
                <Button variant="ghost" class="mt-4 text-primary font-black" onclick={openCreate}>Configurar mi primera zona</Button>
            </div>
        {:else}
            {#each areas as area}
                <div class="card bg-base-100 shadow-xl border border-base-200 rounded-[2rem] overflow-hidden group hover:shadow-2xl hover:shadow-orange-500/10 transition-all duration-300">
                    <div class="card-body p-8">
                        <div class="flex justify-between items-start mb-4">
                            <div class="p-3 bg-orange-500/10 text-orange-600 rounded-2xl">
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
                            </div>
                            <span class="badge {area.is_active ? 'badge-success' : 'badge-ghost'} font-black text-[9px] p-2">
                                {area.is_active ? 'ACTIVO' : 'INACTIVO'}
                            </span>
                        </div>
                        
                        <h3 class="text-xl font-black text-base-content group-hover:text-primary transition-colors">{area.name}</h3>
                        <p class="text-xs font-medium opacity-50 line-clamp-2 h-8">{area.description || 'Sin descripción adicional.'}</p>
                        
                        <div class="mt-6 flex flex-col gap-2">
                            <div class="flex items-center justify-between bg-base-200/50 p-3 rounded-xl border border-base-300/50">
                                <span class="text-[9px] font-black uppercase tracking-widest opacity-40">Impresora</span>
                                <span class="text-[10px] font-black text-primary">
                                    {area.printer_ip ? `🖨️ ${area.printer_ip}` : 'No configurada'}
                                </span>
                            </div>
                            <div class="flex items-center justify-between bg-base-200/50 p-3 rounded-xl border border-base-300/50">
                                <span class="text-[9px] font-black uppercase tracking-widest opacity-40">Tipo / Puerto</span>
                                <span class="text-[10px] font-bold opacity-60">
                                    {area.printer_type.toUpperCase()} : {area.printer_port}
                                </span>
                            </div>
                        </div>

                        <div class="card-actions justify-end mt-6 pt-4 border-t border-base-200">
                            <Button variant="ghost" size="sm" class="font-black uppercase text-[10px] tracking-widest text-primary" onclick={() => { isModalOpen = true; }}>
                                Gestionar
                            </Button>
                        </div>
                    </div>
                </div>
            {/each}
        {/if}
    </div>
</div>

<ProductionAreaModal 
    isOpen={isModalOpen} 
    onClose={() => { isModalOpen = false; loadData(); }} 
    onRefresh={loadData}
/>
