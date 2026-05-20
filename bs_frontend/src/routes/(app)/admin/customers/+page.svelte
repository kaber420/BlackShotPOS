<script lang="ts">
    import { onMount } from 'svelte';
    import { CustomerService, type Customer } from '$lib/api/customers';
    import Button from '$lib/components/ui/Button.svelte';
    import Toolbar from '$lib/components/ui/Toolbar.svelte';
    import { formatCurrency, formatDate } from '$lib/utils';
    import { appState } from '$lib/app_state.svelte';
    import { toast } from '$lib/toast.svelte.js';


    // Constants
    const TIERS = [
        { value: 'regular', label: 'Regular ☕' },
        { value: 'gold', label: 'VIP Gold 🌟' },
        { value: 'platinum', label: 'VIP Platinum 👑' }
    ];

    // State
    let customers = $state<Customer[]>([]);
    let isLoading = $state(true);
    let error = $state<string | null>(null);
    let successMsg = $state<string | null>(null);
    let searchQuery = $state('');

    // Selected customer & edit state
    let selectedCustomer = $state<Customer | null>(null);
    let editingPoints = $state(false);
    let newPointsVal = $state(0);
    let editingBalance = $state(false);
    let newBalanceVal = $state(0.0);
    let editingNFC = $state(false);
    let newNFCVal = $state('');

    // Modal Create
    let showCreateModal = $state(false);
    let creating = $state(false);
    let createError = $state<string | null>(null);
    let newCustomer = $state({
        name: '',
        username: '',
        password: '',
        phone: '',
        email: ''
    });

    // Preferences Edit
    let editingPrefs = $state(false);
    let editPrefsObj = $state({
        allergies: '',
        preferences_notes: ''
    });

    onMount(loadCustomers);

    async function loadCustomers() {
        isLoading = true;
        error = null;
        try {
            if (searchQuery.trim().length > 0) {
                customers = await CustomerService.search(searchQuery.trim());
            } else {
                customers = await CustomerService.list();
            }
        } catch (e: any) {
            error = e.message;
        } finally {
            isLoading = false;
        }
    }

    // Trigger loading on search query changes (debounced/reactive)
    $effect(() => {
        const query = searchQuery;
        const delayDebounceFn = setTimeout(() => {
            loadCustomers();
        }, 300);
        return () => clearTimeout(delayDebounceFn);
    });

    function selectCustomer(c: Customer) {
        selectedCustomer = c;
        newPointsVal = c.points;
        newBalanceVal = c.credit_balance;
        newNFCVal = c.nfc_tag_id || '';
        editPrefsObj = {
            allergies: c.custom_metadata?.allergies || '',
            preferences_notes: c.custom_metadata?.preferences_notes || ''
        };
        editingPoints = false;
        editingBalance = false;
        editingNFC = false;
        editingPrefs = false;
    }

    async function handleCreate() {
        creating = true;
        createError = null;
        try {
            const created = await CustomerService.create({
                name: newCustomer.name.trim(),
                username: newCustomer.username.trim(),
                password: newCustomer.password.trim(),
                phone: newCustomer.phone.trim() || undefined,
                email: newCustomer.email.trim() || undefined
            });
            flash('✅ Cliente creado correctamente');
            showCreateModal = false;
            newCustomer = { name: '', username: '', password: '', phone: '', email: '' };
            await loadCustomers();
            selectCustomer(created);
        } catch (e: any) {
            createError = e.message;
        } finally {
            creating = false;
        }
    }

    async function handleUpdatePoints() {
        if (!selectedCustomer) return;
        try {
            const updated = await CustomerService.update(selectedCustomer.id, {
                points: newPointsVal
            });
            selectedCustomer = updated;
            editingPoints = false;
            flash('✅ Puntos actualizados');
            await loadCustomers();
        } catch (e: any) {
            error = e.message;
        }
    }

    async function handleUpdateBalance() {
        if (!selectedCustomer) return;
        try {
            const updated = await CustomerService.update(selectedCustomer.id, {
                credit_balance: newBalanceVal
            });
            selectedCustomer = updated;
            editingBalance = false;
            flash('✅ Saldo actualizado');
            await loadCustomers();
        } catch (e: any) {
            error = e.message;
        }
    }

    async function handleUpdateNFC() {
        if (!selectedCustomer) return;
        try {
            const updated = await CustomerService.update(selectedCustomer.id, {
                nfc_tag_id: newNFCVal.trim() || undefined
            });
            selectedCustomer = updated;
            editingNFC = false;
            flash('✅ Tarjeta NFC vinculada');
            await loadCustomers();
        } catch (e: any) {
            error = e.message;
        }
    }

    async function handleUpdatePrefs() {
        if (!selectedCustomer) return;
        try {
            const updated = await CustomerService.update(selectedCustomer.id, {
                custom_metadata: {
                    ...selectedCustomer.custom_metadata,
                    allergies: editPrefsObj.allergies.trim(),
                    preferences_notes: editPrefsObj.preferences_notes.trim()
                }
            });
            selectedCustomer = updated;
            editingPrefs = false;
            flash('✅ Preferencias actualizadas');
            await loadCustomers();
        } catch (e: any) {
            error = e.message;
        }
    }

    async function changeTier(newTier: string) {
        if (!selectedCustomer) return;
        try {
            const updated = await CustomerService.update(selectedCustomer.id, {
                tier: newTier
            });
            selectedCustomer = updated;
            flash('✅ Nivel VIP actualizado');
            await loadCustomers();
        } catch (e: any) {
            error = e.message;
        }
    }

    async function toggleActive() {
        if (!selectedCustomer) return;
        try {
            const updated = await CustomerService.update(selectedCustomer.id, {
                is_active: !selectedCustomer.is_active
            });
            selectedCustomer = updated;
            toast.success(updated.is_active ? 'Cliente activado correctamente' : 'Cliente desactivado correctamente');
            await loadCustomers();
        } catch (e: any) {
            toast.error(e.message || 'Error al actualizar estado del cliente');
        }
    }

    function flash(msg: string) {
        successMsg = msg;
        setTimeout(() => (successMsg = null), 3000);
    }

    function tierBadge(tier: string) {
        const map: Record<string, string> = {
            regular: 'bg-slate-500 text-white border-slate-600/30 shadow-2xs font-extrabold',
            gold: 'badge-warning font-black text-warning-content shadow-sm bg-gradient-to-r from-amber-400 to-yellow-500 border-none',
            platinum: 'badge-secondary font-black text-secondary-content shadow-sm bg-gradient-to-r from-indigo-500 via-purple-600 to-pink-500 border-none'
        };
        return map[tier] ?? 'bg-slate-500 text-white border-slate-600/30 shadow-2xs';
    }

    function tierCardGradient(tier: string) {
        const map: Record<string, string> = {
            regular: 'from-neutral-700 to-neutral-900 border-neutral-600',
            gold: 'from-amber-600 via-yellow-700 to-amber-900 border-amber-500/30',
            platinum: 'from-indigo-900 via-purple-900 to-pink-900 border-purple-500/30'
        };
        return map[tier] ?? 'from-neutral-700 to-neutral-900 border-neutral-600';
    }

    // Modal Edit General
    let showEditModal = $state(false);
    let editingGeneral = $state(false);
    let editError = $state<string | null>(null);
    let editCustomer = $state({
        name: '',
        username: '',
        password: '',
        phone: '',
        email: ''
    });

    // Modal Delete
    let showDeleteModal = $state(false);
    let deleting = $state(false);

    function openEditModal() {
        if (!selectedCustomer) return;
        editCustomer = {
            name: selectedCustomer.name || '',
            username: selectedCustomer.username || '',
            password: '', // Vacía por defecto/seguridad
            phone: selectedCustomer.phone || '',
            email: selectedCustomer.email || ''
        };
        editError = null;
        showEditModal = true;
    }

    async function handleEdit() {
        if (!selectedCustomer) return;
        editingGeneral = true;
        editError = null;
        try {
            const payload: any = {
                name: editCustomer.name.trim(),
                username: editCustomer.username.trim(),
                phone: editCustomer.phone.trim() || undefined,
                email: editCustomer.email.trim() || undefined
            };
            if (editCustomer.password.trim()) {
                payload.password = editCustomer.password.trim();
            }
            const updated = await CustomerService.update(selectedCustomer.id, payload);
            selectedCustomer = updated;
            showEditModal = false;
            toast.success('Cliente actualizado correctamente');
            await loadCustomers();
        } catch (e: any) {
            editError = e.message;
        } finally {
            editingGeneral = false;
        }
    }

    async function handleDelete() {
        if (!selectedCustomer) return;
        deleting = true;
        try {
            await CustomerService.delete(selectedCustomer.id);
            toast.success('Cliente eliminado correctamente');
            showDeleteModal = false;
            selectedCustomer = null;
            await loadCustomers();
        } catch (e: any) {
            toast.error(e.message || 'Error al eliminar el cliente');
        } finally {
            deleting = false;
        }
    }
</script>

<div class="p-6 flex-1 min-h-0 overflow-y-auto w-full space-y-6">

    <!-- Unified Header Toolbar -->
    <Toolbar title="Gestión de Clientes">
        {#snippet left()}
            <a href="/admin" class="btn btn-ghost btn-sm font-black gap-1 rounded-xl uppercase tracking-wider text-xs">
                ← Volver
            </a>
        {/snippet}
        
        {#snippet right()}
            <Button id="btn-create-customer" variant="primary" size="sm" class="gap-2 rounded-xl font-bold"
                onclick={() => (showCreateModal = true)}>
                <svelte:fragment slot="icon">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
                    </svg>
                </svelte:fragment>
                Nuevo Cliente
            </Button>
        {/snippet}
    </Toolbar>

    <!-- Alertas -->
    {#if successMsg}
        <div class="alert alert-success mb-4 shadow-sm font-bold">
            {successMsg}
        </div>
    {/if}
    {#if error}
        <div class="alert alert-error mb-4 shadow-sm">
            <span>{error}</span>
            <Button variant="ghost" circle size="xs" onclick={() => (error = null)}>✕</Button>
        </div>
    {/if}

    <!-- Layout lista + detalle -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

        <!-- Lista de clientes -->
        <div class="lg:col-span-1 flex flex-col gap-3">
            <div class="form-control w-full mb-2">
                <input 
                    type="text" 
                    placeholder="Buscar por usuario, QR o NFC..." 
                    class="input input-bordered w-full rounded-3xl bg-base-100 border-base-content/10 font-bold focus:border-primary/50 focus:ring-2 focus:ring-primary/20 transition-all duration-300"
                    bind:value={searchQuery}
                />
            </div>

            {#if isLoading}
                <div class="flex justify-center p-12">
                    <span class="loading loading-spinner loading-lg text-primary"></span>
                </div>
            {:else if customers.length === 0}
                <div class="text-center p-8 bg-base-100/50 rounded-[2.5rem] border border-dashed opacity-40">
                    <p class="text-4xl mb-2">👥</p>
                    <p class="font-bold">Ningún cliente encontrado</p>
                    <p class="text-sm">Escribe un parámetro de búsqueda exacto o crea uno nuevo</p>
                </div>
            {:else}
                {#each customers as c (c.id)}
                    <!-- svelte-ignore a11y_click_events_have_key_events -->
                    <!-- svelte-ignore a11y_no_static_element_interactions -->
                    <div
                        class="bg-base-100 rounded-[2rem] border cursor-pointer transition-all duration-300 hover:shadow-lg hover:-translate-y-0.5
                            {selectedCustomer?.id === c.id 
                                ? 'border-primary/40 bg-primary/5 shadow-md ring-2 ring-primary/10' 
                                : 'border-base-content/5 shadow-xs'}"
                        onclick={() => selectCustomer(c)}
                    >
                        <div class="p-5 flex flex-row items-center justify-between gap-2">
                            <div class="flex items-center gap-3">
                                <div class="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-lg font-black">
                                    {(c.username || c.name || 'CL').substring(0,2).toUpperCase()}
                                </div>
                                <div>
                                    <p class="font-bold leading-tight flex items-center gap-1.5 flex-wrap">
                                        <span>{c.name || c.username || 'Cliente Sin Nombre'}</span>
                                        {#if c.name && c.username}
                                            <span class="text-[10px] bg-blue-50 text-blue-700 border border-blue-200/60 font-mono font-black px-1.5 py-0.5 rounded-md">@{c.username}</span>
                                        {/if}
                                    </p>
                                    <div class="flex items-center gap-1.5 mt-1.5">
                                        <span class="text-[10px] font-mono font-black text-slate-100 bg-slate-700 px-1.5 py-0.5 rounded-md border border-slate-800/20 shadow-2xs">{c.loyalty_code}</span>
                                        <span class="badge badge-xs font-black uppercase text-[9px] tracking-wider {tierBadge(c.tier)}">
                                            {c.tier}
                                        </span>
                                        {#if !c.is_active}
                                            <span class="badge badge-xs badge-error font-extrabold text-[9px] uppercase tracking-wider">Inactivo</span>
                                        {/if}
                                    </div>
                                </div>
                            </div>
                            <div class="text-right shrink-0">
                                <p class="text-sm font-black text-primary font-mono">{c.points} pts</p>
                                <p class="text-xs font-black text-success font-mono">{formatCurrency(c.credit_balance)}</p>
                            </div>
                        </div>
                    </div>
                {/each}
            {/if}
        </div>

        <!-- Panel detalle -->
        <div class="lg:col-span-2">
            {#if selectedCustomer}
                <div class="bg-base-100 rounded-[2.5rem] border border-base-content/5 shadow-xl hover:shadow-2xl transition-all duration-500 overflow-hidden relative">
                    <!-- Glassmorphism decorative background glow -->
                    <div class="absolute -top-32 -right-32 w-96 h-96 bg-primary/5 rounded-full blur-3xl pointer-events-none"></div>
                    
                    <div class="p-6 md:p-8 gap-6 flex flex-col relative z-10">
                        <!-- Cabecera de Datos Integrada con Tarjeta Virtual -->
                        <div class="flex flex-col lg:flex-row gap-6 pb-6 border-b border-base-200 items-stretch">
                            <!-- Columna Tarjeta Física Virtual -->
                            <div class="w-full lg:w-[320px] shrink-0 flex items-center justify-center bg-base-200/30 p-4 rounded-3xl border border-base-200/50">
                                <div class="w-full aspect-[1.58/1] rounded-2xl bg-gradient-to-br {tierCardGradient(selectedCustomer.tier)} p-5 text-white border flex flex-col justify-between shadow-lg relative overflow-hidden transition-all duration-500 hover:scale-[1.02] hover:shadow-xl">
                                    <!-- Glow effects -->
                                    <div class="absolute -right-16 -top-16 w-36 h-36 bg-white/5 rounded-full blur-2xl pointer-events-none"></div>
                                    
                                    <div class="flex justify-between items-start">
                                        <div>
                                            <h3 class="text-base font-black tracking-tight uppercase">{selectedCustomer.tier} CLUB</h3>
                                            <span class="text-[8px] uppercase tracking-[0.15em] text-white/70 font-black">
                                                {appState.settings?.name?.toUpperCase() || 'SOCIO EXCLUSIVO'}
                                            </span>
                                        </div>
                                        <span class="text-2xl">☕</span>
                                    </div>

                                    <div class="space-y-2">
                                        <div>
                                            <p class="text-[7.5px] uppercase tracking-widest text-white/70 font-black mb-0.5">ID de Socio</p>
                                            <p class="text-xs font-mono font-black tracking-tight truncate">@{selectedCustomer.username}</p>
                                        </div>
                                        
                                        <div class="flex justify-between items-end">
                                            <div>
                                                <p class="text-[7.5px] uppercase tracking-widest text-white/70 font-black mb-0.5">Código de Fidelidad</p>
                                                <p class="font-mono text-[10px] tracking-[0.2em] font-black">{selectedCustomer.loyalty_code}</p>
                                            </div>
                                            <div class="text-right">
                                                <p class="text-[7.5px] uppercase tracking-widest text-white/70 font-black mb-0.5">Saldo Digital</p>
                                                <p class="font-mono text-sm font-black">{formatCurrency(selectedCustomer.credit_balance)}</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Columna Datos e Identidad del Cliente -->
                            <div class="flex-1 flex flex-col justify-between gap-4">
                                <div class="flex items-start justify-between pb-2 flex-wrap gap-3">
                                    <div>
                                        <h2 class="text-2xl font-black">{selectedCustomer.name || selectedCustomer.username}</h2>
                                        <div class="flex items-center gap-2 mt-2">
                                            <span class="text-xs font-extrabold text-base-content/60">Username:</span>
                                            <span class="inline-flex items-center gap-0.5 bg-primary/10 border border-primary/20 text-primary text-xs font-mono font-black px-2.5 py-0.5 rounded-xl shadow-xs">
                                                <span class="opacity-40 select-none">@</span>{selectedCustomer.username}
                                            </span>
                                        </div>
                                    </div>
                                    <div class="flex gap-2 flex-wrap">
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            class="rounded-xl font-bold"
                                            onclick={openEditModal}>
                                            ✏️ Editar Datos
                                        </Button>
                                        <Button
                                            variant="outline"
                                            danger={selectedCustomer.is_active}
                                            success={!selectedCustomer.is_active}
                                            size="sm"
                                            class="rounded-xl font-bold"
                                            onclick={toggleActive}>
                                            {selectedCustomer.is_active ? '🚫 Desactivar Cuenta' : '✅ Activar Cuenta'}
                                        </Button>
                                        <Button
                                            variant="outline"
                                            danger={true}
                                            size="sm"
                                            class="rounded-xl font-bold border-red-500/30 hover:bg-red-500/10 text-red-500"
                                            onclick={() => (showDeleteModal = true)}>
                                            🗑️ Eliminar Cliente
                                        </Button>
                                    </div>
                                </div>

                                <!-- Selectores de NFC y Membresía Integrados en 2 Columnas -->
                                <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-auto pt-2">
                                    <!-- Selector de Membresía VIP -->
                                    <div class="form-control">
                                        <span class="text-[9px] font-extrabold uppercase tracking-widest text-base-content/60 mb-2">Nivel de Membresía VIP</span>
                                        <div class="flex gap-1.5 flex-wrap">
                                            {#each TIERS as t}
                                                <button 
                                                    class="btn btn-xs rounded-xl font-black uppercase tracking-wider transition-all
                                                        {selectedCustomer.tier === t.value ? 'btn-primary shadow-xs' : 'btn-outline opacity-60'}"
                                                    onclick={() => changeTier(t.value)}
                                                >
                                                    {t.label}
                                                </button>
                                            {/each}
                                        </div>
                                    </div>

                                    <!-- Vinculación de Tarjeta NFC -->
                                    <div class="form-control">
                                        <span class="text-[9px] font-extrabold uppercase tracking-widest text-base-content/60 mb-2">Tarjeta NFC Vinculada</span>
                                        {#if editingNFC}
                                            <div class="flex gap-2">
                                                <input type="text" class="input input-bordered input-xs rounded-lg font-bold font-mono w-full" placeholder="Aproxima la tarjeta..." bind:value={newNFCVal}/>
                                                <Button variant="success" size="xs" onclick={handleUpdateNFC}>💾</Button>
                                                <Button variant="ghost" size="xs" onclick={() => editingNFC = false}>✕</Button>
                                            </div>
                                        {:else}
                                            <div class="flex items-center gap-2">
                                                <span class="text-lg leading-none">💳</span>
                                                <span class="font-mono font-bold text-xs {selectedCustomer.nfc_tag_id ? 'text-primary' : 'opacity-40'}">
                                                    {selectedCustomer.nfc_tag_id || 'Sin vincular'}
                                                </span>
                                                <button class="text-xs text-primary font-bold hover:underline ml-auto" onclick={() => editingNFC = true}>
                                                    ✏️ {selectedCustomer.nfc_tag_id ? 'Editar' : 'Vincular'}
                                                </button>
                                            </div>
                                        {/if}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Panel de Datos Financieros & Lealtad -->
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 pb-6 border-b border-base-200">
                            
                            <!-- Columna Puntos de Fidelidad -->
                            <div class="bg-base-200/50 p-5 rounded-3xl border border-base-200 flex flex-col justify-between">
                                <div>
                                    <span class="text-[10px] font-extrabold uppercase tracking-widest text-base-content/75">Puntos Acumulados</span>
                                    {#if editingPoints}
                                        <div class="flex gap-2 mt-2">
                                            <input type="number" class="input input-bordered input-sm rounded-xl font-bold font-mono w-24" bind:value={newPointsVal}/>
                                            <Button variant="success" size="sm" onclick={handleUpdatePoints}>💾</Button>
                                            <Button variant="ghost" size="sm" onclick={() => editingPoints = false}>✕</Button>
                                        </div>
                                    {:else}
                                        <div class="flex items-baseline gap-2 mt-2">
                                            <h4 class="text-3xl font-black text-primary font-mono">{selectedCustomer.points}</h4>
                                            <span class="text-xs font-bold opacity-40">pts</span>
                                        </div>
                                    {/if}
                                </div>
                                {#if !editingPoints}
                                    <button class="text-xs font-black text-primary hover:underline mt-4 text-left" onclick={() => editingPoints = true}>
                                        ✏️ Modificar Puntos
                                    </button>
                                {/if}
                            </div>

                            <!-- Columna Monedero Digital -->
                            <div class="bg-base-200/50 p-5 rounded-3xl border border-base-200 flex flex-col justify-between">
                                <div>
                                    <span class="text-[10px] font-extrabold uppercase tracking-widest text-base-content/75">Crédito Prepago</span>
                                    {#if editingBalance}
                                        <div class="flex gap-2 mt-2">
                                            <input type="number" step="0.01" class="input input-bordered input-sm rounded-xl font-bold font-mono w-28" bind:value={newBalanceVal}/>
                                            <Button variant="success" size="sm" onclick={handleUpdateBalance}>💾</Button>
                                            <Button variant="ghost" size="sm" onclick={() => editingBalance = false}>✕</Button>
                                        </div>
                                    {:else}
                                        <div class="flex items-baseline gap-2 mt-2">
                                            <h4 class="text-3xl font-black text-success font-mono">{formatCurrency(selectedCustomer.credit_balance)}</h4>
                                        </div>
                                    {/if}
                                </div>
                                {#if !editingBalance}
                                    <button class="text-xs font-black text-success hover:underline mt-4 text-left" onclick={() => editingBalance = true}>
                                        ✏️ Recargar / Ajustar Saldo
                                    </button>
                                {/if}
                            </div>
                        </div>

                        <!-- Preferencias y Notas (Alergias, etc) -->
                        <div class="space-y-4">
                            <div class="flex items-center justify-between">
                                <h3 class="font-black text-lg">Preferencias y Notas</h3>
                                {#if !editingPrefs}
                                    <Button variant="ghost" size="xs" onclick={() => editingPrefs = true}>✏️ Editar Preferencias</Button>
                                {/if}
                            </div>

                            {#if editingPrefs}
                                <div class="space-y-4 p-4 bg-base-200/50 rounded-2xl border">
                                    <div class="form-control">
                                        <label class="label" for="allergies">
                                            <span class="label-text font-bold">Alergias</span>
                                        </label>
                                        <input id="allergies" type="text" class="input input-bordered rounded-xl" bind:value={editPrefsObj.allergies} placeholder="ej. Gluten, Lácteos"/>
                                    </div>
                                    <div class="form-control">
                                        <label class="label" for="prefs-notes">
                                            <span class="label-text font-bold">Instrucciones de Preparación</span>
                                        </label>
                                        <textarea id="prefs-notes" class="textarea textarea-bordered rounded-xl h-20" bind:value={editPrefsObj.preferences_notes} placeholder="ej. Prefiere café cortado bien caliente con leche de coco..."></textarea>
                                    </div>
                                    <div class="flex justify-end gap-2">
                                        <Button variant="ghost" size="sm" onclick={() => editingPrefs = false}>Cancelar</Button>
                                        <Button variant="primary" size="sm" onclick={handleUpdatePrefs}>Guardar Preferencias</Button>
                                    </div>
                                </div>
                            {:else}
                                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div class="p-4 bg-error/5 rounded-2xl border border-error/10">
                                        <span class="text-[9px] font-black uppercase text-error tracking-wider">⚠️ Alergias Declaradas</span>
                                        <p class="text-sm font-bold text-error-content mt-1">
                                            {selectedCustomer.custom_metadata?.allergies || 'Ninguna alergia registrada'}
                                        </p>
                                    </div>
                                    <div class="p-4 bg-base-200/50 rounded-2xl border">
                                        <span class="text-[9px] font-extrabold uppercase text-base-content/75 tracking-wider">📝 Notas de Preparación</span>
                                        <p class="text-sm font-semibold opacity-80 mt-1">
                                            {selectedCustomer.custom_metadata?.preferences_notes || 'Sin instrucciones adicionales de preparación'}
                                        </p>
                                    </div>
                                </div>
                            {/if}
                        </div>

                    </div>
                </div>
            {:else}
                <div class="bg-base-100/50 rounded-[2.5rem] border border-dashed border-base-300 min-h-64 flex items-center justify-center">
                    <div class="text-center p-8 max-w-sm">
                        <p class="text-5xl mb-4 animate-bounce">👈</p>
                        <p class="font-black text-xl text-base-content/85 mb-2">Selecciona un cliente</p>
                        <p class="text-sm text-base-content/60 font-medium">para ver sus finanzas, saldo de monedero y preferencias</p>
                    </div>
                </div>
            {/if}
        </div>
    </div>
</div>

<!-- Modal Crear Cliente -->
{#if showCreateModal}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div class="modal modal-open z-50" onclick={() => (showCreateModal = false)}>
        <div class="modal-box rounded-3xl" onclick={(e) => e.stopPropagation()}>
            <h3 class="font-black text-xl mb-4 flex items-center gap-2">
                <span>➕</span> Nuevo Registro de Cliente (Portal Local)
            </h3>
            {#if createError}
                <div class="alert alert-error mb-4 text-sm font-bold">{createError}</div>
            {/if}
            <div class="flex flex-col gap-4">
                <div class="form-control">
                    <label class="label" for="new-cust-name">
                        <span class="label-text font-bold">Nombre Completo</span>
                    </label>
                    <input id="new-cust-name" type="text" class="input input-bordered rounded-xl font-bold"
                        placeholder="ej. Juan Pérez" bind:value={newCustomer.name} autocomplete="off"/>
                </div>
                <div class="form-control">
                    <label class="label" for="new-cust-username">
                        <span class="label-text font-bold">Nombre de usuario (Login Portal)</span>
                    </label>
                    <input id="new-cust-username" type="text" class="input input-bordered rounded-xl font-bold"
                        placeholder="ej. juan_cafecito" bind:value={newCustomer.username} autocomplete="off"/>
                </div>
                <div class="form-control">
                    <label class="label" for="new-cust-password">
                        <span class="label-text font-bold">Contraseña (Login Portal)</span>
                    </label>
                    <input id="new-cust-password" type="password" class="input input-bordered rounded-xl"
                        placeholder="••••••••" bind:value={newCustomer.password}/>
                </div>
                <div class="form-control">
                    <label class="label" for="new-cust-phone">
                        <span class="label-text font-bold">Teléfono (Opcional)</span>
                    </label>
                    <input id="new-cust-phone" type="text" class="input input-bordered rounded-xl font-mono font-bold"
                        placeholder="ej. 5512345678" bind:value={newCustomer.phone} autocomplete="off"/>
                </div>
                <div class="form-control">
                    <label class="label" for="new-cust-email">
                        <span class="label-text font-bold">Email (Opcional)</span>
                    </label>
                    <input id="new-cust-email" type="email" class="input input-bordered rounded-xl font-bold"
                        placeholder="ej. juan@example.com" bind:value={newCustomer.email} autocomplete="off"/>
                </div>
            </div>
            <div class="modal-action">
                <Button variant="ghost" onclick={() => (showCreateModal = false)}>Cancelar</Button>
                <Button id="btn-confirm-create-customer" variant="primary"
                    onclick={handleCreate}
                    disabled={!newCustomer.name.trim() || !newCustomer.username.trim() || !newCustomer.password.trim()}
                    isLoading={creating}>
                    Registrar Cliente
                </Button>
            </div>
        </div>
    </div>
{/if}

<!-- Modal Editar Cliente -->
{#if showEditModal}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div class="modal modal-open z-50" onclick={() => (showEditModal = false)}>
        <div class="modal-box rounded-3xl" onclick={(e) => e.stopPropagation()}>
            <h3 class="font-black text-xl mb-4 flex items-center gap-2">
                <span>✏️</span> Editar Datos del Cliente
            </h3>
            {#if editError}
                <div class="alert alert-error mb-4 text-sm font-bold">{editError}</div>
            {/if}
            <div class="flex flex-col gap-4">
                <div class="form-control">
                    <label class="label" for="edit-cust-name">
                        <span class="label-text font-bold">Nombre Completo</span>
                    </label>
                    <input id="edit-cust-name" type="text" class="input input-bordered rounded-xl font-bold"
                        placeholder="ej. Juan Pérez" bind:value={editCustomer.name} autocomplete="off"/>
                </div>
                <div class="form-control">
                    <label class="label" for="edit-cust-username">
                        <span class="label-text font-bold">Nombre de usuario (Login Portal)</span>
                    </label>
                    <input id="edit-cust-username" type="text" class="input input-bordered rounded-xl font-bold"
                        placeholder="ej. juan_cafecito" bind:value={editCustomer.username} autocomplete="off"/>
                </div>
                <div class="form-control">
                    <label class="label" for="edit-cust-password">
                        <span class="label-text font-bold">Contraseña</span>
                    </label>
                    <input id="edit-cust-password" type="password" class="input input-bordered rounded-xl"
                        placeholder="Dejar en blanco para conservar actual" bind:value={editCustomer.password}/>
                </div>
                <div class="form-control">
                    <label class="label" for="edit-cust-phone">
                        <span class="label-text font-bold">Teléfono (Opcional)</span>
                    </label>
                    <input id="edit-cust-phone" type="text" class="input input-bordered rounded-xl font-mono font-bold"
                        placeholder="ej. 5512345678" bind:value={editCustomer.phone} autocomplete="off"/>
                </div>
                <div class="form-control">
                    <label class="label" for="edit-cust-email">
                        <span class="label-text font-bold">Email (Opcional)</span>
                    </label>
                    <input id="edit-cust-email" type="email" class="input input-bordered rounded-xl font-bold"
                        placeholder="ej. juan@example.com" bind:value={editCustomer.email} autocomplete="off"/>
                </div>
            </div>
            <div class="modal-action">
                <Button variant="ghost" onclick={() => (showEditModal = false)}>Cancelar</Button>
                <Button id="btn-confirm-edit-customer" variant="primary"
                    onclick={handleEdit}
                    disabled={!editCustomer.name.trim() || !editCustomer.username.trim()}
                    isLoading={editingGeneral}>
                    Guardar Cambios
                </Button>
            </div>
        </div>
    </div>
{/if}

<!-- Modal Confirmación de Eliminación Segura -->
{#if showDeleteModal}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div class="modal modal-open z-50" onclick={() => (showDeleteModal = false)}>
        <div class="modal-box rounded-3xl border border-red-500/20 max-w-md" onclick={(e) => e.stopPropagation()}>
            <div class="flex items-center gap-3 text-red-500 mb-4">
                <span class="text-3xl">⚠️</span>
                <h3 class="font-black text-xl">¿Eliminar cliente permanentemente?</h3>
            </div>
            
            <p class="text-sm opacity-85 leading-relaxed mb-6">
                Esta acción eliminará físicamente el registro de <strong class="text-red-500">@{selectedCustomer?.username}</strong>. Sus consumos históricos, transacciones y reservaciones serán desvinculados de forma limpia, pero <strong>se mantendrá la contabilidad financiera y el historial de ventas intactos</strong> en el sistema de auditoría. Esta acción no se puede deshacer.
            </p>

            <div class="modal-action gap-2">
                <Button variant="ghost" onclick={() => (showDeleteModal = false)}>Cancelar</Button>
                <Button id="btn-confirm-delete-customer" variant="primary" danger={true}
                    onclick={handleDelete}
                    isLoading={deleting}>
                    Confirmar Eliminación
                </Button>
            </div>
        </div>
    </div>
{/if}


<style>
    /* Styling overrides */
    .btn {
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
</style>
