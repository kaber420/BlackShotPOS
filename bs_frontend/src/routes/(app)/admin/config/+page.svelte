<script lang="ts">
    /**
     * Blackshot POS - Configuration Hub
     * -----------------------------------------------------
     * Centralized control center for business settings, infrastructure, and technology.
     */
    import { onMount } from 'svelte';
    import { appState, setTheme } from '$lib/app_state.svelte';
    import { SettingsService, type BusinessSettings } from '$lib/api/settings';
    import { toastConfig, saveToastConfig, addToast } from '$lib/toast.svelte.js';
    import Button from '$lib/components/ui/Button.svelte';
    import ProductionAreaModal from '$lib/components/ProductionAreaModal.svelte';
    import { goto } from '$app/navigation';

    let settings = $state<BusinessSettings>({ ...appState.settings });
    let isLoading = $state(false);
    
    // UI State
    let activeSection = $state<'hub' | 'general' | 'finance' | 'appearance' | 'bridge'>('hub');
    let isProductionModalOpen = $state(false);

    async function handleSave() {
        isLoading = true;
        try {
            const updated = await SettingsService.update(settings);
            appState.settings = updated;
            saveToastConfig();
            addToast("¡Configuración guardada!", "success");
            activeSection = 'hub'; // Return to hub after saving
        } catch (e) {
            addToast("Error al guardar: " + e, "error");
        } finally {
            isLoading = false;
        }
    }

    const hubCards = [
        {
            id: 'general',
            title: 'Datos del Negocio',
            desc: 'Nombre, dirección y datos del establecimiento.',
            icon: '🏢',
            color: 'bg-blue-500/10 text-blue-600',
            action: () => activeSection = 'general'
        },
        {
            id: 'finance',
            title: 'Finanzas e Impuestos',
            desc: 'Moneda, tasas de IVA y localización.',
            icon: '💰',
            color: 'bg-emerald-500/10 text-emerald-600',
            action: () => activeSection = 'finance'
        },
        {
            id: 'production',
            title: 'Áreas de Producción',
            desc: 'Configura Cocina, Bar e Impresoras.',
            icon: '🍳',
            color: 'bg-orange-500/10 text-orange-600',
            action: () => isProductionModalOpen = true
        },
        {
            id: 'inventory',
            title: 'Gestión de Inventario',
            desc: 'Control de insumos, stock y proveedores.',
            icon: '📦',
            color: 'bg-indigo-500/10 text-indigo-600',
            action: () => goto('/inventory')
        },
        {
            id: 'tables',
            title: 'Mesas y Salones',
            desc: 'Diseño del mapa y gestión de espacios.',
            icon: '🪑',
            color: 'bg-amber-500/10 text-amber-600',
            action: () => goto('/tables')
        },
        {
            id: 'devices',
            title: 'Dispositivos IoT',
            desc: 'Antenas Intercom y periféricos externos.',
            icon: '🔌',
            color: 'bg-purple-500/10 text-purple-600',
            action: () => goto('/admin/devices')
        },
        {
            id: 'audits',
            title: 'Bitácora de Auditoría',
            desc: 'Registro global de eventos y seguridad.',
            icon: '🛡️',
            color: 'bg-slate-500/10 text-slate-600',
            action: () => goto('/admin/audits')
        },
        {
            id: 'bridge',
            title: 'Sincronización Central',
            desc: 'Configuración de Bridge y nubes externas.',
            icon: '☁️',
            color: 'bg-cyan-500/10 text-cyan-600',
            action: () => activeSection = 'bridge'
        },
        {
            id: 'appearance',
            title: 'Personalización',
            desc: 'Estilo de notificaciones y temas visuales.',
            icon: '🎨',
            color: 'bg-pink-500/10 text-pink-600',
            action: () => activeSection = 'appearance'
        }
    ];

</script>

<div class="p-6 lg:p-10 max-w-6xl mx-auto flex-1 min-h-0 overflow-y-auto w-full space-y-10">
    
    <!-- Header -->
    <header class="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
            <div class="flex items-center gap-3 mb-2">
                {#if activeSection !== 'hub'}
                    <button 
                        class="btn btn-ghost btn-sm btn-circle bg-base-300/50 hover:bg-base-300"
                        onclick={() => activeSection = 'hub'}
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="3" stroke="currentColor" class="w-4 h-4"><path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" /></svg>
                    </button>
                {/if}
                <h1 class="text-4xl font-black tracking-tight text-base-content uppercase">
                    Centro de <span class="text-primary">Control</span>
                </h1>
            </div>
            <p class="text-base-content/60 font-medium ml-1">
                {activeSection === 'hub' ? 'Gestiona la infraestructura y configuración de tu negocio.' : 'Ajusta los parámetros específicos de esta sección.'}
            </p>
        </div>
    </header>

    {#if activeSection === 'hub'}
        <!-- Hub Grid -->
        <section class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {#each hubCards as card}
                <button 
                    onclick={card.action}
                    class="card bg-base-100 shadow-xl hover:shadow-2xl hover:scale-[1.02] active:scale-95 transition-all duration-300 border border-base-200 group text-left"
                >
                    <div class="card-body p-8 gap-4">
                        <div class="w-14 h-14 {card.color} rounded-2xl flex items-center justify-center text-3xl shadow-sm group-hover:scale-110 transition-transform">
                            {card.icon}
                        </div>
                        <div>
                            <h3 class="text-xl font-black text-base-content group-hover:text-primary transition-colors">{card.title}</h3>
                            <p class="text-sm font-medium opacity-50 mt-1">{card.desc}</p>
                        </div>
                        <div class="card-actions justify-end mt-2">
                            <span class="text-[10px] font-black uppercase tracking-widest opacity-30 group-hover:opacity-100 group-hover:text-primary transition-all">Abrir Sección →</span>
                        </div>
                    </div>
                </button>
            {/each}
        </section>
    {:else}
        <!-- Content Sections (Forms) -->
        <div class="animate-in fade-in slide-in-from-bottom-4 duration-400">
            <div class="card bg-base-100 shadow-2xl border border-base-200 rounded-[2.5rem] overflow-hidden">
                <div class="card-body p-10 gap-8">
                    
                    {#if activeSection === 'general'}
                        <h2 class="text-2xl font-black uppercase flex items-center gap-3">
                            <span class="w-2 h-8 bg-blue-500 rounded-full"></span>
                            Datos del Establecimiento
                        </h2>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                            <div class="form-control w-full">
                                <label class="label"><span class="label-text font-black text-[10px] uppercase opacity-50">Nombre del Negocio</span></label>
                                <input type="text" bind:value={settings.name} class="input input-bordered font-bold focus:border-primary rounded-xl" />
                            </div>
                            <div class="form-control w-full">
                                <label class="label"><span class="label-text font-black text-[10px] uppercase opacity-50">Dirección en Ticket</span></label>
                                <textarea bind:value={settings.address} class="textarea textarea-bordered font-bold h-24 focus:border-primary rounded-xl"></textarea>
                            </div>
                            <div class="form-control w-full">
                                <label class="label"><span class="label-text font-black text-[10px] uppercase opacity-50">Pie de Página del Ticket</span></label>
                                <input type="text" bind:value={settings.ticket_footer} class="input input-bordered font-bold focus:border-primary rounded-xl" />
                            </div>
                        </div>
                    {/if}

                    {#if activeSection === 'finance'}
                        <h2 class="text-2xl font-black uppercase flex items-center gap-3">
                            <span class="w-2 h-8 bg-emerald-500 rounded-full"></span>
                            Finanzas e Impuestos
                        </h2>
                        <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
                            <div class="form-control w-full">
                                <label class="label"><span class="label-text font-black text-[10px] uppercase opacity-50">Símbolo de Moneda</span></label>
                                <input type="text" bind:value={settings.currency_symbol} class="input input-bordered font-bold text-center focus:border-primary rounded-xl" />
                            </div>
                            <div class="form-control w-full">
                                <label class="label"><span class="label-text font-black text-[10px] uppercase opacity-50">Código ISO</span></label>
                                <input type="text" bind:value={settings.currency_code} class="input input-bordered font-bold text-center focus:border-primary rounded-xl" placeholder="MXN" />
                            </div>
                            <div class="form-control w-full">
                                <label class="label"><span class="label-text font-black text-[10px] uppercase opacity-50">Tasa IVA (%)</span></label>
                                <input type="number" step="0.01" bind:value={settings.tax_rate} class="input input-bordered font-bold text-center focus:border-primary rounded-xl" />
                            </div>
                        </div>
                    {/if}

                    {#if activeSection === 'bridge'}
                        <h2 class="text-2xl font-black uppercase flex items-center gap-3">
                            <span class="w-2 h-8 bg-cyan-500 rounded-full"></span>
                            Sincronización Central (Bridge)
                        </h2>
                        <div class="bg-base-200/50 p-8 rounded-[2rem] border border-base-300 space-y-6">
                            <div class="flex justify-between items-center">
                                <div>
                                    <h4 class="font-black text-lg">Estado del Bridge</h4>
                                    <p class="text-xs font-medium opacity-50">Habilita la comunicación con el Panel Central.</p>
                                </div>
                                <input type="checkbox" bind:checked={settings.bridge_enabled} class="toggle toggle-primary toggle-lg" />
                            </div>
                            
                            {#if settings.bridge_enabled}
                                <div class="grid grid-cols-1 md:grid-cols-2 gap-6 animate-in fade-in slide-in-from-top-2">
                                    <div class="form-control w-full">
                                        <label class="label"><span class="label-text font-black text-[10px] uppercase opacity-50">Branch ID</span></label>
                                        <input type="text" bind:value={settings.branch_id} class="input input-bordered font-mono text-xs focus:border-primary bg-base-100 rounded-xl" />
                                    </div>
                                    <div class="form-control w-full">
                                        <label class="label"><span class="label-text font-black text-[10px] uppercase opacity-50">NATS Server URL</span></label>
                                        <input type="text" bind:value={settings.nats_url} class="input input-bordered font-mono text-xs focus:border-primary bg-base-100 rounded-xl" />
                                    </div>
                                    <div class="form-control w-full md:col-span-2">
                                        <label class="label"><span class="label-text font-black text-[10px] uppercase opacity-50">Public Key (PEM)</span></label>
                                        <textarea bind:value={settings.bridge_public_key} class="textarea textarea-bordered font-mono text-[10px] h-32 focus:border-primary bg-base-100 rounded-xl"></textarea>
                                    </div>
                                </div>
                            {/if}
                        </div>
                    {/if}

                    {#if activeSection === 'appearance'}
                        <h2 class="text-2xl font-black uppercase flex items-center gap-3">
                            <span class="w-2 h-8 bg-pink-500 rounded-full"></span>
                            Personalización Visual
                        </h2>
                        <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
                            <div class="form-control w-full">
                                <label class="label"><span class="label-text font-black text-[10px] uppercase opacity-50">Forma de Notificaciones</span></label>
                                <select bind:value={toastConfig.shape} class="select select-bordered font-bold focus:border-primary rounded-xl">
                                    <option value="bean">Semilla (Original)</option>
                                    <option value="square">Cuadrado (Moderno)</option>
                                </select>
                            </div>
                            <div class="form-control w-full">
                                <label class="label"><span class="label-text font-black text-[10px] uppercase opacity-50">Posición</span></label>
                                <select bind:value={toastConfig.position} class="select select-bordered font-bold focus:border-primary rounded-xl">
                                    <option value="bottom-right">Abajo-Derecha</option>
                                    <option value="bottom-center">Abajo-Centro</option>
                                    <option value="top-right">Arriba-Derecha</option>
                                </select>
                            </div>
                            <div class="form-control w-full">
                                <label class="label"><span class="label-text font-black text-[10px] uppercase opacity-50">Tamaño Texto</span></label>
                                <select bind:value={toastConfig.fontSize} class="select select-bordered font-bold focus:border-primary rounded-xl">
                                    <option value="0.75rem">Pequeño</option>
                                    <option value="0.9rem">Medio</option>
                                    <option value="1.1rem">Grande</option>
                                </select>
                            </div>
                        </div>

                        <div class="space-y-4">
                            <h3 class="text-lg font-black uppercase flex items-center gap-2 opacity-70">
                                <span class="w-1.5 h-5 bg-pink-500 rounded-full"></span>
                                Tema del Sistema
                            </h3>
                            <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                                {#each ['corporate', 'coffee', 'bumblebee', 'light', 'dark', 'dim'] as theme}
                                    <button 
                                        class="flex flex-col items-center gap-3 p-4 rounded-2xl border-2 transition-all {appState.currentTheme === theme ? 'border-primary bg-primary/5' : 'border-base-200 bg-base-100 hover:border-base-300'}"
                                        onclick={() => setTheme(theme)}
                                    >
                                        <div data-theme={theme} class="w-full aspect-video rounded-lg shadow-inner flex flex-col p-1 gap-1 bg-base-100 overflow-hidden border border-base-content/10">
                                            <div class="h-2 w-full bg-primary rounded-full"></div>
                                            <div class="h-2 w-3/4 bg-secondary rounded-full"></div>
                                            <div class="h-2 w-1/2 bg-accent rounded-full"></div>
                                        </div>
                                        <span class="text-[10px] font-black uppercase tracking-widest">{theme}</span>
                                    </button>
                                {/each}
                            </div>
                        </div>

                        <div class="grid grid-cols-1 md:grid-cols-2 gap-8 bg-base-200/50 p-8 rounded-[2rem]">
                            <div class="flex items-center gap-4">
                                <div class="flex-1">
                                    <label class="label"><span class="label-text font-bold">Fondo Notificación</span></label>
                                    <input type="color" bind:value={toastConfig.backgroundColor} class="w-full h-12 rounded-xl border-0 p-0 cursor-pointer" />
                                </div>
                                <div class="flex-1">
                                    <label class="label"><span class="label-text font-bold">Color Texto</span></label>
                                    <input type="color" bind:value={toastConfig.textColor} class="w-full h-12 rounded-xl border-0 p-0 cursor-pointer" />
                                </div>
                            </div>
                            <div class="flex flex-col justify-center">
                                <label class="label cursor-pointer justify-start gap-4">
                                    <input type="checkbox" bind:checked={toastConfig.hasShadow} class="toggle toggle-secondary" />
                                    <span class="label-text font-bold">Habilitar Sombras</span>
                                </label>
                            </div>
                        </div>
                    {/if}

                    <div class="card-actions justify-end mt-10 pt-8 border-t border-base-200">
                        <Button variant="ghost" size="lg" class="px-8 font-bold opacity-50" onclick={() => activeSection = 'hub'}>Cancelar</Button>
                        <Button variant="primary" size="lg" class="px-12 font-black uppercase tracking-widest text-xs" onclick={handleSave} {isLoading}>Guardar Cambios</Button>
                    </div>
                </div>
            </div>
        </div>
    {/if}
</div>

<ProductionAreaModal 
    isOpen={isProductionModalOpen} 
    onClose={() => isProductionModalOpen = false} 
/>

<style>
    .card {
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    }
</style>
