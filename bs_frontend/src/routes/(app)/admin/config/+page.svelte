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
    import TaxModal from '$lib/components/TaxModal.svelte';
    import { ProductService } from '$lib/api/products';
    import { goto } from '$app/navigation';

    let settings = $state<BusinessSettings>({ ...appState.settings });
    let isLoading = $state(false);
    
    // UI State
    let activeSection = $state<'hub' | 'general' | 'finance' | 'appearance' | 'bridge'>('hub');
    let isProductionModalOpen = $state(false);
    let isTaxModalOpen = $state(false);

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

    async function handleBackgroundUpload(event: Event) {
        const input = event.target as HTMLInputElement;
        if (!input.files || input.files.length === 0) return;

        isLoading = true;
        try {
            const file = input.files[0];
            const response = await ProductService.uploadImage(file);
            settings.menu_background_url = response.url;
            addToast("Imagen de fondo subida con éxito", "success");
        } catch (e) {
            addToast("Error al subir imagen: " + e, "error");
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
        },
        {
            id: 'menu',
            title: 'Carta Digital',
            desc: 'Personaliza títulos, footer y redes sociales.',
            icon: '📜',
            color: 'bg-rose-500/10 text-rose-600',
            action: () => activeSection = 'menu'
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
                        <div class="flex justify-between items-center mb-6">
                            <h2 class="text-2xl font-black uppercase flex items-center gap-3">
                                <span class="w-2 h-8 bg-emerald-500 rounded-full"></span>
                                Finanzas e Impuestos
                            </h2>
                            <Button variant="primary" size="sm" onclick={() => isTaxModalOpen = true}>
                                Gestionar Tipos de Impuestos
                            </Button>
                        </div>
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

                    {#if activeSection === 'menu'}
                        <h2 class="text-2xl font-black uppercase flex items-center gap-3">
                            <span class="w-2 h-8 bg-rose-500 rounded-full"></span>
                            Configuración de Carta Digital
                        </h2>
                        
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                            <div class="space-y-6">
                                <h3 class="text-lg font-black uppercase flex items-center gap-2 opacity-70">
                                    <span class="w-1.5 h-5 bg-rose-400 rounded-full"></span>
                                    Encabezado y Textos
                                </h3>
                                <div class="form-control w-full">
                                    <label class="label"><span class="label-text font-black text-[10px] uppercase opacity-50">Título de la Carta</span></label>
                                    <input type="text" bind:value={settings.menu_title} class="input input-bordered font-bold focus:border-primary rounded-xl" />
                                </div>
                                <div class="form-control w-full">
                                    <label class="label"><span class="label-text font-black text-[10px] uppercase opacity-50">Subtítulo / Frase</span></label>
                                    <input type="text" bind:value={settings.menu_subtitle} class="input input-bordered font-bold focus:border-primary rounded-xl" />
                                </div>
                                <div class="form-control w-full">
                                    <label class="label"><span class="label-text font-black text-[10px] uppercase opacity-50">URL del Logo (Opcional)</span></label>
                                    <input type="text" bind:value={settings.menu_logo_url} class="input input-bordered font-mono text-xs focus:border-primary rounded-xl" placeholder="https://ejemplo.com/logo.png" />
                                </div>
                                
                                <div class="form-control w-full">
                                    <label class="label">
                                        <span class="label-text font-black text-[10px] uppercase opacity-50">Imagen de Fondo de la Carta</span>
                                    </label>
                                    <div class="flex flex-col gap-4">
                                        {#if settings.menu_background_url}
                                            <div class="relative w-full h-32 rounded-2xl overflow-hidden border border-base-300 bg-base-200 group">
                                                <img src={settings.menu_background_url} alt="Background Preview" class="w-full h-full object-cover" />
                                                <button 
                                                    class="absolute inset-0 bg-black/50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                                                    onclick={() => settings.menu_background_url = ''}
                                                >
                                                    <span class="text-white font-black text-[10px] uppercase tracking-widest">Eliminar</span>
                                                </button>
                                            </div>
                                        {/if}
                                        <div class="flex gap-2">
                                            <input 
                                                type="file" 
                                                accept="image/*" 
                                                class="file-input file-input-bordered file-input-primary w-full rounded-xl" 
                                                onchange={handleBackgroundUpload}
                                                disabled={isLoading}
                                            />
                                        </div>
                                        <input type="text" bind:value={settings.menu_background_url} class="input input-bordered font-mono text-[10px] focus:border-primary rounded-xl" placeholder="URL manual o subida..." />
                                    </div>
                                </div>
                            </div>

                            <div class="space-y-6">
                                <h3 class="text-lg font-black uppercase flex items-center gap-2 opacity-70">
                                    <span class="w-1.5 h-5 bg-rose-400 rounded-full"></span>
                                    Footer (Pie de Página)
                                </h3>
                                <div class="form-control w-full">
                                    <label class="label"><span class="label-text font-black text-[10px] uppercase opacity-50">Texto Principal Footer</span></label>
                                    <input type="text" bind:value={settings.menu_footer_text} class="input input-bordered font-bold focus:border-primary rounded-xl" />
                                </div>
                                <div class="form-control w-full">
                                    <label class="label"><span class="label-text font-black text-[10px] uppercase opacity-50">Tagline del Footer</span></label>
                                    <input type="text" bind:value={settings.menu_footer_tagline} class="input input-bordered font-bold focus:border-primary rounded-xl" />
                                </div>
                                <div class="form-control w-full">
                                    <label class="label"><span class="label-text font-black text-[10px] uppercase opacity-50">Color de Acento (Hex)</span></label>
                                    <div class="flex gap-2">
                                        <input type="color" bind:value={settings.menu_accent_color} class="w-12 h-12 rounded-xl cursor-pointer" />
                                        <input type="text" bind:value={settings.menu_accent_color} class="input input-bordered font-mono flex-1 rounded-xl" />
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="space-y-6 mt-4">
                            <h3 class="text-lg font-black uppercase flex items-center gap-2 opacity-70">
                                <span class="w-1.5 h-5 bg-rose-400 rounded-full"></span>
                                Redes Sociales (URLs)
                            </h3>
                            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                                <div class="form-control w-full">
                                    <label class="label"><span class="label-text font-black text-[10px] uppercase opacity-50 text-blue-600">Facebook</span></label>
                                    <input type="text" bind:value={settings.menu_facebook_url} class="input input-bordered text-sm rounded-xl focus:border-blue-500" placeholder="https://facebook.com/..." />
                                </div>
                                <div class="form-control w-full">
                                    <label class="label"><span class="label-text font-black text-[10px] uppercase opacity-50 text-pink-600">Instagram</span></label>
                                    <input type="text" bind:value={settings.menu_instagram_url} class="input input-bordered text-sm rounded-xl focus:border-pink-500" placeholder="https://instagram.com/..." />
                                </div>
                                <div class="form-control w-full">
                                    <label class="label"><span class="label-text font-black text-[10px] uppercase opacity-50 text-red-600">YouTube</span></label>
                                    <input type="text" bind:value={settings.menu_youtube_url} class="input input-bordered text-sm rounded-xl focus:border-red-500" placeholder="https://youtube.com/..." />
                                </div>
                                <div class="form-control w-full">
                                    <label class="label"><span class="label-text font-black text-[10px] uppercase opacity-50 text-sky-500">Twitter / X</span></label>
                                    <input type="text" bind:value={settings.menu_twitter_url} class="input input-bordered text-sm rounded-xl focus:border-sky-500" placeholder="https://x.com/..." />
                                </div>
                                <div class="form-control w-full">
                                    <label class="label"><span class="label-text font-black text-[10px] uppercase opacity-50 text-emerald-600">TikTok</span></label>
                                    <input type="text" bind:value={settings.menu_tiktok_url} class="input input-bordered text-sm rounded-xl focus:border-emerald-500" placeholder="https://tiktok.com/@..." />
                                </div>
                                <div class="form-control w-full">
                                    <label class="label"><span class="label-text font-black text-[10px] uppercase opacity-50 text-green-500">WhatsApp</span></label>
                                    <input type="text" bind:value={settings.menu_whatsapp_url} class="input input-bordered text-sm rounded-xl focus:border-green-500" placeholder="https://wa.me/..." />
                                </div>
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

<TaxModal
    isOpen={isTaxModalOpen}
    onClose={() => isTaxModalOpen = false}
/>

<style>
    .card {
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    }
</style>
