<script lang="ts">
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { fade, fly, slide } from 'svelte/transition';
    import { quintOut } from 'svelte/easing';

    interface CustomerData {
        id: string;
        name: string;
        phone: string | null;
        email: string | null;
        username: string | null;
        loyalty_code: string;
        points: number;
        credit_balance: number;
        tier: string;
        custom_metadata: {
            preferences_notes?: string;
            allergies?: string;
            [key: string]: any;
        };
    }

    let customer = $state<CustomerData | null>(null);
    let isLoading = $state(true);
    let isSaving = $state(false);
    let errorMessage = $state('');
    let saveSuccess = $state(false);

    // Form fields for editing preferences
    let prefNotes = $state('');
    let prefAllergies = $state('');

    async function loadProfile() {
        isLoading = true;
        errorMessage = '';
        try {
            const token = localStorage.getItem('customer_token');
            if (!token) {
                goto('/login');
                return;
            }

            const response = await fetch(`/api/v1/public/customers/me`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.status === 401 || response.status === 403) {
                localStorage.removeItem('customer_token');
                goto('/login');
                return;
            }

            if (!response.ok) throw new Error('Error al obtener datos del servidor');

            const data = await response.json();
            customer = data;
            
            // Populate form fields
            prefNotes = customer?.custom_metadata?.preferences_notes || '';
            prefAllergies = customer?.custom_metadata?.allergies || '';
        } catch (error) {
            console.error('Error loading profile:', error);
            errorMessage = 'No se pudo cargar tu perfil. Revisa tu conexión.';
        } finally {
            isLoading = false;
        }
    }

    async function savePreferences(e: Event) {
        e.preventDefault();
        if (!customer) return;
        
        isSaving = true;
        errorMessage = '';
        saveSuccess = false;
        
        try {
            const token = localStorage.getItem('customer_token');
            if (!token) {
                goto('/login');
                return;
            }

            const updatedMetadata = {
                ...customer.custom_metadata,
                preferences_notes: prefNotes,
                allergies: prefAllergies
            };

            const response = await fetch(`/api/v1/public/customers/me/preferences`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ custom_metadata: updatedMetadata })
            });

            if (!response.ok) throw new Error('Error al guardar preferencias');

            const data = await response.json();
            customer = data;
            saveSuccess = true;
            setTimeout(() => {
                saveSuccess = false;
            }, 3000);
        } catch (error) {
            console.error('Error saving preferences:', error);
            errorMessage = 'Error al guardar tus preferencias.';
        } finally {
            isSaving = false;
        }
    }

    function logout() {
        localStorage.removeItem('customer_token');
        goto('/login');
    }

    onMount(() => {
        loadProfile();
    });

    // Helper to resolve card colors based on membership tier
    const cardStyle = $derived(() => {
        const tierName = customer?.tier?.toLowerCase() || 'regular';
        if (tierName === 'gold' || tierName === 'oro') {
            return {
                bg: 'bg-gradient-to-br from-[#d4af37] via-[#f3e5ab] to-[#aa7c11] text-black shadow-amber-500/20',
                badge: 'bg-black/25 text-black border-black/10',
                tierLabel: 'VIP Gold'
            };
        } else if (tierName === 'platinum' || tierName === 'platino') {
            return {
                bg: 'bg-gradient-to-br from-[#3a3d40] via-[#b8c6db] to-[#3a3d40] text-black shadow-slate-500/20',
                badge: 'bg-black/20 text-black border-black/10',
                tierLabel: 'VIP Platinum'
            };
        }
        // Default / Regular
        return {
            bg: 'bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-600 text-white shadow-purple-500/20',
            badge: 'bg-white/20 text-white border-white/10',
            tierLabel: 'Socio Regular'
        };
    });
</script>

<svelte:head>
    <title>Mi Perfil | BlackShot</title>
</svelte:head>

<div class="min-h-screen bg-base-100 pb-24">
    <div class="max-w-4xl mx-auto px-4 pt-8">
        
        <!-- Header minimalista -->
        <header class="flex justify-between items-center mb-10" in:fade={{ duration: 400 }}>
            <button 
                onclick={() => goto('/menu')}
                class="btn btn-ghost rounded-2xl flex items-center gap-2 font-black uppercase text-xs tracking-wider opacity-70 hover:opacity-100"
            >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
                </svg>
                Volver al Menú
            </button>
            <button 
                onclick={logout}
                class="btn btn-outline border-base-300 rounded-2xl font-black uppercase text-xs tracking-wider opacity-60 hover:opacity-100 hover:bg-error hover:text-error-content hover:border-error"
            >
                Cerrar Sesión
            </button>
        </header>

        {#if isLoading}
            <div class="flex flex-col items-center justify-center py-32 gap-4">
                <span class="loading loading-spinner loading-lg text-primary"></span>
                <span class="text-xs uppercase tracking-[0.2em] font-black opacity-40">Cargando tu cuenta...</span>
            </div>
        {:else if errorMessage && !customer}
            <div class="text-center py-20 bg-base-200/40 rounded-[3rem] border border-base-200 p-8" in:fly={{ y: 20, duration: 400 }}>
                <div class="w-16 h-16 bg-error/10 text-error rounded-full flex items-center justify-center mx-auto mb-4 border border-error/20">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                </div>
                <h2 class="text-xl font-black uppercase tracking-tight mb-2">Error de Conexión</h2>
                <p class="text-xs opacity-60 mb-6 max-w-sm mx-auto">{errorMessage}</p>
                <button onclick={loadProfile} class="btn btn-primary rounded-2xl font-black uppercase tracking-wider px-8">Reintentar</button>
            </div>
        {:else if customer}
            <div class="grid grid-cols-1 md:grid-cols-12 gap-8" in:fly={{ y: 30, duration: 600, easing: quintOut }}>
                
                <!-- Columna Izquierda: Tarjeta Digital VIP & QR -->
                <div class="md:col-span-6 flex flex-col gap-8">
                    
                    <!-- VIP Card Glassmorphic -->
                    <div 
                        class="aspect-[1.586/1] w-full rounded-[2.5rem] p-6 md:p-8 flex flex-col justify-between relative overflow-hidden shadow-2xl transition-transform duration-500 hover:scale-[1.02] {cardStyle().bg}"
                    >
                        <!-- Glow effect -->
                        <div class="absolute inset-0 bg-white/5 opacity-40 mix-blend-overlay"></div>
                        
                        <div class="flex justify-between items-start z-10">
                            <div>
                                <h3 class="text-[10px] uppercase tracking-[0.2em] font-black opacity-60 mb-1">Blackshot Club</h3>
                                <p class="text-lg md:text-2xl font-black uppercase tracking-tighter truncate max-w-[200px]">
                                    {customer.name}
                                </p>
                            </div>
                            <span class="text-[9px] uppercase tracking-widest font-black border px-3 py-1 rounded-full backdrop-blur-md {cardStyle().badge}">
                                {cardStyle().tierLabel}
                            </span>
                        </div>

                        <div class="grid grid-cols-2 gap-4 z-10 border-t border-black/5 pt-4 mt-6">
                            <div>
                                <span class="text-[8px] uppercase tracking-wider font-black opacity-50 block mb-0.5">Saldo Monedero</span>
                                <span class="text-xl md:text-2xl font-mono font-black tracking-tight">${customer.credit_balance.toFixed(2)}</span>
                            </div>
                            <div>
                                <span class="text-[8px] uppercase tracking-wider font-black opacity-50 block mb-0.5">Puntos Acumulados</span>
                                <span class="text-xl md:text-2xl font-mono font-black tracking-tight">{customer.points} pts</span>
                            </div>
                        </div>
                    </div>

                    <!-- QR Code Card -->
                    <div class="bg-base-200/50 backdrop-blur-xl border border-base-200 rounded-[3rem] p-8 text-center flex flex-col items-center justify-center shadow-xl">
                        <h3 class="text-sm font-black uppercase tracking-widest mb-2">Mi Código de Lealtad</h3>
                        <p class="text-[10px] uppercase opacity-40 font-bold mb-6 tracking-wider">Presenta este código en caja al pagar</p>
                        
                        <!-- QR Frame Frame -->
                        <div class="bg-white p-5 rounded-[2rem] shadow-inner mb-6 transition-all duration-500 hover:shadow-2xl hover:scale-[1.03] border border-base-200">
                            <img 
                                src="https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={customer.loyalty_code}" 
                                alt="Loyalty QR Code" 
                                class="w-48 h-48 select-none"
                            />
                        </div>
                        
                        <div class="font-mono font-black tracking-[0.2em] text-lg bg-base-300/40 px-6 py-2 rounded-2xl border border-base-300/50 text-base-content/70 select-all">
                            {customer.loyalty_code}
                        </div>
                    </div>

                </div>

                <!-- Columna Derecha: Preferencias & Información Adicional -->
                <div class="md:col-span-6 flex flex-col gap-8">
                    
                    <!-- Form de Preferencias -->
                    <div class="bg-base-200/50 backdrop-blur-xl border border-base-200 rounded-[3rem] p-8 shadow-xl">
                        <div class="flex items-center gap-3 mb-6">
                            <div class="w-10 h-10 bg-primary/10 rounded-2xl flex items-center justify-center text-primary border border-primary/20">
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
                                </svg>
                            </div>
                            <div>
                                <h3 class="text-lg font-black uppercase tracking-tight">Preferencias Personales</h3>
                                <p class="text-[9px] uppercase tracking-wider opacity-40 font-bold">Personaliza tu experiencia de café</p>
                            </div>
                        </div>

                        {#if errorMessage}
                            <div class="alert alert-error text-xs font-bold mb-4 rounded-xl">{errorMessage}</div>
                        {/if}

                        {#if saveSuccess}
                            <div class="alert alert-success text-xs font-black uppercase tracking-wider mb-4 rounded-xl text-center" in:slide>
                                ¡Preferencias actualizadas con éxito!
                            </div>
                        {/if}

                        <form onsubmit={savePreferences} class="flex flex-col gap-6">
                            <div class="form-control">
                                <label class="label" for="allergies">
                                    <span class="label-text text-[10px] uppercase font-black tracking-widest opacity-60">Alergias o Restricciones</span>
                                </label>
                                <input 
                                    type="text" 
                                    id="allergies" 
                                    bind:value={prefAllergies} 
                                    placeholder="Ej. Intolerante a la lactosa, alergia a las nueces" 
                                    class="input input-bordered w-full rounded-2xl bg-base-300/30 border-none focus:ring-2 focus:ring-primary/20 font-medium text-sm h-12"
                                />
                            </div>

                            <div class="form-control">
                                <label class="label" for="notes">
                                    <span class="label-text text-[10px] uppercase font-black tracking-widest opacity-60">Notas de Preparación Favoritas</span>
                                </label>
                                <textarea 
                                    id="notes" 
                                    bind:value={prefNotes} 
                                    rows="4"
                                    placeholder="Ej. Espresso con doble carga de agua, leche de avena bien vaporizada, azúcar mascabado..." 
                                    class="textarea textarea-bordered w-full rounded-2xl bg-base-300/30 border-none focus:ring-2 focus:ring-primary/20 font-medium text-sm p-4 resize-none"
                                ></textarea>
                            </div>

                            <button 
                                type="submit" 
                                class="btn btn-primary btn-lg w-full rounded-2xl mt-2 font-black uppercase tracking-widest"
                                disabled={isSaving}
                            >
                                {#if isSaving}
                                    <span class="loading loading-spinner"></span> Guardando...
                                {:else}
                                    Guardar Cambios
                                {/if}
                            </button>
                        </form>
                    </div>

                    <!-- Datos Informativos de la Cuenta -->
                    <div class="bg-base-200/30 border border-base-200/50 rounded-[3rem] p-8 flex flex-col gap-4">
                        <h3 class="text-xs uppercase font-black tracking-wider opacity-40 mb-2">Información de Cuenta</h3>
                        
                        {#if customer.username}
                            <div class="flex justify-between items-center text-xs pb-3 border-b border-base-200/50">
                                <span class="font-bold opacity-60">Usuario</span>
                                <span class="font-mono font-black">{customer.username}</span>
                            </div>
                        {/if}
                        
                        {#if customer.phone}
                            <div class="flex justify-between items-center text-xs pb-3 border-b border-base-200/50">
                                <span class="font-bold opacity-60">Teléfono registrado</span>
                                <span class="font-mono font-black">{customer.phone}</span>
                            </div>
                        {/if}
                        
                        {#if customer.email}
                            <div class="flex justify-between items-center text-xs pb-3 border-b border-base-200/50">
                                <span class="font-bold opacity-60">Email</span>
                                <span class="font-mono font-black">{customer.email}</span>
                            </div>
                        {/if}
                    </div>

                </div>

            </div>
        {/if}

    </div>
</div>

<style>
    :global(.textarea:focus), :global(.input:focus) {
        outline: none !important;
    }
</style>
