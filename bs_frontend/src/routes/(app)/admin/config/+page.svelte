<script lang="ts">
    /**
     * Blackshot POS - Business Settings & Toast Customization
     * -----------------------------------------------------
     * A clean administrative interface for managing system-wide settings.
     */
    import { onMount } from 'svelte';
    import { appState } from '$lib/app_state.svelte';
    import { SettingsService, type BusinessSettings } from '$lib/api/settings';
    import { toastConfig, saveToastConfig, addToast } from '$lib/toast.svelte.js';
    import Button from '$lib/components/ui/Button.svelte';

    let settings = $state<BusinessSettings>({ ...appState.settings });
    let isLoading = $state(false);
    let message = $state({ text: '', type: '' });

    async function handleSave() {
        isLoading = true;
        message = { text: '', type: '' };
        try {
            const updated = await SettingsService.update(settings);
            appState.settings = updated;
            
            // Perist local toast settings
            saveToastConfig();
            
            addToast("¡Configuración guardada!", "success", 2500);
            message = { text: 'Configuración guardada con éxito', type: 'success' };
            
            setTimeout(() => { message = { text: '', type: '' } }, 3000);
        } catch (e) {
            message = { text: 'Error al ahorrar: ' + e, type: 'error' };
        } finally {
            isLoading = false;
        }
    }
</script>

<div class="p-6 lg:p-10 max-w-4xl mx-auto flex-1 min-h-0 overflow-y-auto w-full">
    <div class="flex flex-col gap-1 mb-10">
        <h1 class="text-4xl font-black tracking-tight flex items-center gap-3 uppercase">
            <div class="w-12 h-12 bg-primary rounded-2xl flex items-center justify-center text-primary-content shadow-lg shadow-primary/20">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-7 h-7">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12a7.5 7.5 0 0015 0m-15 0a7.5 7.5 0 1115 0m-15 0H3m16.5 0H21m-1.5 0H12m-8.457 3.077l1.41-.513m14.095-5.13l1.41-.513M5.106 17.785l1.15-.964m11.49-9.642l1.149-.964M7.501 19.795l.75-1.3m7.5-12.99l.75-1.3m2.743 14.293l-.75-1.3m-7.5-12.99l-.75-1.3m5.132 15.213l-1.41-.513m-14.095-5.13l-1.41-.513M18.894 6.215l-1.15.963m-11.49 9.642l-1.149.964M16.5 4.205l-.75 1.3m-7.5 12.99l-.75 1.3" />
                </svg>
            </div>
            Configuración del Sistema
        </h1>
        <p class="text-base-content/60 font-medium ml-1">Gestiona los datos de tu negocio y la apariencia de la aplicación.</p>
    </div>

    {#if message.text}
        <div class="alert alert-{message.type} mb-6 shadow-md animate-in fade-in slide-in-from-top-4">
            <span>{message.text}</span>
        </div>
    {/if}

    <div class="card bg-base-100 shadow-xl border border-base-200">
        <div class="card-body gap-8">
            <!-- Section: Business Information -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-10">
                <div class="flex flex-col gap-6">
                    <h3 class="text-xs font-black uppercase tracking-[0.2em] text-primary opacity-60">Datos del Establecimiento</h3>
                    
                    <div class="form-control w-full">
                        <label class="label"><span class="label-text font-bold">Nombre del Negocio</span></label>
                        <input type="text" bind:value={settings.name} class="input input-bordered font-bold focus:border-primary" />
                    </div>

                    <div class="form-control w-full">
                        <label class="label"><span class="label-text font-bold">Dirección Ticket</span></label>
                        <textarea bind:value={settings.address} class="textarea textarea-bordered font-bold h-24 focus:border-primary"></textarea>
                    </div>
                </div>

                <div class="flex flex-col gap-6">
                    <h3 class="text-xs font-black uppercase tracking-[0.2em] text-primary opacity-60">Finanzas</h3>
                    
                    <div class="grid grid-cols-2 gap-4">
                        <div class="form-control w-full">
                            <label class="label"><span class="label-text font-bold">Símbolo</span></label>
                            <input type="text" bind:value={settings.currency_symbol} class="input input-bordered font-bold text-center focus:border-primary" />
                        </div>
                        <div class="form-control w-full">
                            <label class="label"><span class="label-text font-bold">Código (ISO)</span></label>
                            <input type="text" bind:value={settings.currency_code} class="input input-bordered font-bold text-center focus:border-primary" placeholder="MXN" />
                        </div>
                    </div>

                    <div class="grid grid-cols-2 gap-4">
                        <div class="form-control w-full">
                            <label class="label"><span class="label-text font-bold">IVA (%)</span></label>
                            <input type="number" step="0.01" bind:value={settings.tax_rate} class="input input-bordered font-bold text-center focus:border-primary" />
                        </div>
                        <div class="form-control w-full">
                            <label class="label"><span class="label-text font-bold">Localización (Locale)</span></label>
                            <input type="text" bind:value={settings.locale} class="input input-bordered font-bold text-center focus:border-primary" placeholder="es-MX" />
                        </div>
                    </div>

                    <div class="form-control w-full">
                        <label class="label"><span class="label-text font-bold">Pie de Página Ticket</span></label>
                        <input type="text" bind:value={settings.ticket_footer} class="input input-bordered font-bold focus:border-primary" />
                    </div>
                </div>
            </div>

            <div class="divider"></div>

            <!-- Section: Bridge Configuration -->
            <div class="flex flex-col gap-6 bg-primary/5 p-6 rounded-2xl border border-primary/10">
                <div class="flex justify-between items-center">
                    <div>
                        <h3 class="text-sm font-black uppercase tracking-[0.2em] text-primary">Gestión Remota & Sincronización Central</h3>
                        <p class="text-xs font-medium opacity-60 mt-1">Permite que el Panel Central administre esta sucursal de forma segura.</p>
                    </div>
                    <div class="form-control">
                        <label class="label cursor-pointer gap-4">
                            <span class="label-text font-bold">Habilitar Bridge</span>
                            <input type="checkbox" bind:checked={settings.bridge_enabled} class="toggle toggle-primary" />
                        </label>
                    </div>
                </div>
                
                {#if settings.bridge_enabled}
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 animate-in fade-in slide-in-from-top-2">
                        <div class="form-control w-full">
                            <label class="label"><span class="label-text font-bold">Branch ID</span></label>
                            <input type="text" bind:value={settings.branch_id} class="input input-bordered font-mono text-sm focus:border-primary bg-base-300/50" placeholder="Ej. 550e8400-e29b-41d4-a716-446655440000" />
                        </div>
                        <div class="form-control w-full">
                            <label class="label"><span class="label-text font-bold">NATS URL</span></label>
                            <input type="text" bind:value={settings.nats_url} class="input input-bordered font-mono text-sm focus:border-primary bg-base-300/50" placeholder="Ej. nats://tu-servidor:4222" />
                        </div>
                    </div>
                    <div class="form-control w-full animate-in fade-in slide-in-from-top-2 mt-2">
                        <label class="label">
                            <span class="label-text font-bold flex items-center gap-2">
                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 text-primary">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z" />
                                </svg>
                                Llave Pública del Bridge (PEM)
                            </span>
                        </label>
                        <textarea 
                            bind:value={settings.bridge_public_key} 
                            class="textarea textarea-bordered font-mono text-[10px] h-32 focus:border-primary bg-base-300/50" 
                            placeholder="-----BEGIN PUBLIC KEY-----..."
                        ></textarea>
                    </div>
                {/if}
            </div>

            <div class="divider"></div>

            <!-- Section: Toast Configuration (Simplified) -->
            <div class="flex flex-col gap-6">
                <h3 class="text-xs font-black uppercase tracking-[0.2em] text-secondary">Ajustes Visuales (Notificaciones)</h3>
                
                <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
                    <div class="form-control w-full">
                        <label class="label"><span class="label-text font-bold">Forma de la Notificación</span></label>
                        <select bind:value={toastConfig.shape} class="select select-bordered font-bold focus:border-primary" onchange={() => addToast("¡Estilo actualizado!", "info", 1500)}>
                            <option value="bean">Semilla (Clásico Blackshot)</option>
                            <option value="square">Rectangular (Moderno)</option>
                        </select>
                    </div>

                    <div class="form-control w-full">
                        <label class="label"><span class="label-text font-bold">Posición en Pantalla</span></label>
                        <select bind:value={toastConfig.position} class="select select-bordered font-bold focus:border-primary" onchange={() => addToast("Posición de notificaciones", "info", 1500)}>
                            <option value="bottom-right">Abajo - Derecha</option>
                            <option value="bottom-center">Abajo - Centro</option>
                            <option value="bottom-left">Abajo - Izquierda</option>
                            <option value="top-right">Arriba - Derecha</option>
                            <option value="top-center">Arriba - Centro</option>
                            <option value="top-left">Arriba - Izquierda</option>
                        </select>
                    </div>

                    <div class="form-control w-full">
                        <label class="label"><span class="label-text font-bold">Tamaño de Fuente</span></label>
                        <select bind:value={toastConfig.fontSize} class="select select-bordered font-bold focus:border-primary" onchange={() => addToast("Tamaño de texto", "info", 1500)}>
                            <option value="0.75rem">Pequeño</option>
                            <option value="0.9rem">Estándar</option>
                            <option value="1.1rem">Grande</option>
                        </select>
                    </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-4 gap-6 bg-base-200/50 p-6 rounded-2xl border border-base-200">
                    <div class="form-control">
                        <label class="label"><span class="label-text font-bold">Color Fondo</span></label>
                        <input type="color" bind:value={toastConfig.backgroundColor} class="w-full h-10 rounded-lg cursor-pointer p-0 border-0" oninput={() => addToast("Tono actualizado", "info", 500)} />
                    </div>
                    <div class="form-control">
                        <label class="label"><span class="label-text font-bold">Color Texto</span></label>
                        <input type="color" bind:value={toastConfig.textColor} class="w-full h-10 rounded-lg cursor-pointer p-0 border-0" oninput={() => addToast("Tono actualizado", "info", 500)} />
                    </div>
                    <div class="form-control col-span-2">
                        <label class="label">
                            <span class="label-text font-bold">Efectos Especiales</span>
                        </label>
                        <div class="flex items-center gap-6 mt-2">
                            <label class="flex items-center gap-2 cursor-pointer">
                                <span class="text-xs font-black opacity-60">Sombra</span>
                                <input type="checkbox" bind:checked={toastConfig.hasShadow} class="toggle toggle-primary toggle-sm" onchange={() => addToast("Sombra controlada", "info", 1000)} />
                            </label>
                            <label class="flex flex-col gap-1 flex-1">
                                <span class="text-[10px] font-black uppercase opacity-40">Vidrio (Blur: {toastConfig.blur}px)</span>
                                <input type="range" min="0" max="25" bind:value={toastConfig.blur} class="range range-xs range-secondary" oninput={() => addToast("Efecto de cristal", "info", 500)} />
                            </label>
                        </div>
                    </div>
                </div>
            </div>

            <div class="card-actions justify-end mt-4 pt-6 border-t border-base-200">
                <Button 
                    variant="primary"
                    size="lg" 
                    class="px-12 font-black uppercase tracking-widest text-sm" 
                    onclick={handleSave}
                    {isLoading}
                >
                    Guardar Cambios
                </Button>
            </div>
        </div>
    </div>
</div>
