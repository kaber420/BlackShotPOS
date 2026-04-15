<script lang="ts">
    import { onMount } from 'svelte';
    import { appState } from '$lib/app_state.svelte';
    import { SettingsService, type BusinessSettings } from '$lib/api/settings';

    let settings = $state<BusinessSettings>({ ...appState.settings });
    let isLoading = $state(false);
    let message = $state({ text: '', type: '' });

    async function handleSave() {
        isLoading = true;
        message = { text: '', type: '' };
        try {
            const updated = await SettingsService.update(settings);
            appState.settings = updated;
            message = { text: 'Configuración guardada con éxito', type: 'success' };
            setTimeout(() => { message = { text: '', type: '' } }, 3000);
        } catch (e) {
            message = { text: 'Error al ahorrar: ' + e, type: 'error' };
        } finally {
            isLoading = false;
        }
    }
</script>

<div class="p-6 lg:p-10 max-w-4xl mx-auto">
    <div class="flex flex-col gap-1 mb-10">
        <h1 class="text-4xl font-black tracking-tight flex items-center gap-3 uppercase">
            <div class="w-12 h-12 bg-primary rounded-2xl flex items-center justify-center text-primary-content shadow-lg shadow-primary/20">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-7 h-7">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12a7.5 7.5 0 0015 0m-15 0a7.5 7.5 0 1115 0m-15 0H3m16.5 0H21m-1.5 0H12m-8.457 3.077l1.41-.513m14.095-5.13l1.41-.513M5.106 17.785l1.15-.964m11.49-9.642l1.149-.964M7.501 19.795l.75-1.3m7.5-12.99l.75-1.3m2.743 14.293l-.75-1.3m-7.5-12.99l-.75-1.3m5.132 15.213l-1.41-.513m-14.095-5.13l-1.41-.513M18.894 6.215l-1.15.963m-11.49 9.642l-1.149.964M16.5 4.205l-.75 1.3m-7.5 12.99l-.75 1.3" />
                </svg>
            </div>
            Configuración del Sistema
        </h1>
        <p class="text-base-content/60 font-medium ml-1">Personaliza los datos de tu negocio, impuestos y tickets.</p>
    </div>

    {#if message.text}
        <div class="alert alert-{message.type} mb-6 shadow-lg animate-in fade-in slide-in-from-top-4">
            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            <span class="font-bold">{message.text}</span>
        </div>
    {/if}

    <div class="card bg-base-100 shadow-xl border border-base-200">
        <div class="card-body gap-8">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-6">
                <!-- Business Info -->
                <div class="flex flex-col gap-6">
                    <h3 class="font-black text-sm uppercase tracking-widest opacity-40">Datos Generales</h3>
                    
                    <div class="form-control w-full">
                        <label class="label"><span class="label-text font-bold opacity-70">Nombre del Negocio</span></label>
                        <input type="text" bind:value={settings.name} class="input input-bordered font-bold focus:border-primary" />
                    </div>

                    <div class="form-control w-full">
                        <label class="label"><span class="label-text font-bold opacity-70">Dirección</span></label>
                        <textarea bind:value={settings.address} class="textarea textarea-bordered font-bold h-24 focus:border-primary"></textarea>
                    </div>

                    <div class="form-control w-full">
                        <label class="label"><span class="label-text font-bold opacity-70">Teléfono</span></label>
                        <input type="text" bind:value={settings.phone} class="input input-bordered font-bold focus:border-primary" />
                    </div>
                </div>

                <!-- Financial Info -->
                <div class="flex flex-col gap-6">
                    <h3 class="font-black text-sm uppercase tracking-widest opacity-40">Finanzas e Impuestos</h3>

                    <div class="grid grid-cols-2 gap-4">
                        <div class="form-control w-full">
                            <label class="label"><span class="label-text font-bold opacity-70">Símbolo Moneda</span></label>
                            <input type="text" bind:value={settings.currency_symbol} class="input input-bordered font-bold text-center focus:border-primary" />
                        </div>
                        <div class="form-control w-full">
                            <label class="label"><span class="label-text font-bold opacity-70">Código Moneda</span></label>
                            <input type="text" bind:value={settings.currency_code} class="input input-bordered font-bold text-center focus:border-primary" />
                        </div>
                    </div>

                    <div class="form-control w-full">
                        <label class="label">
                            <span class="label-text font-bold opacity-70">Tasa de Impuesto (IVA)</span>
                            <span class="label-text-alt font-black text-primary">{(settings.tax_rate * 100).toFixed(0)}%</span>
                        </label>
                        <div class="join w-full">
                           <input type="number" step="0.01" bind:value={settings.tax_rate} class="input input-bordered join-item w-full font-bold focus:border-primary" />
                           <span class="join-item btn btn-active pointer-events-none">%</span>
                        </div>
                        <label class="label"><span class="label-text-alt opacity-50">Usa formato decimal (ej. 0.16 para 16%)</span></label>
                    </div>

                    <div class="form-control w-full">
                        <label class="label"><span class="label-text font-bold opacity-70">Pie de Página Ticket</span></label>
                        <input type="text" bind:value={settings.ticket_footer} class="input input-bordered font-bold focus:border-primary" />
                    </div>
                </div>
            </div>

            <div class="card-actions justify-end mt-4 pt-6 border-t border-base-200">
                <button 
                    class="btn btn-primary px-10 shadow-lg shadow-primary/20 font-black uppercase tracking-widest" 
                    onclick={handleSave}
                    disabled={isLoading}
                >
                    {#if isLoading}
                        <span class="loading loading-spinner"></span> Guardando...
                    {:else}
                        Guardar Cambios
                    {/if}
                </button>
            </div>
        </div>
    </div>
</div>
