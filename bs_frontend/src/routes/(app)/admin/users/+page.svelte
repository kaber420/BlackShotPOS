<script lang="ts">
    import { onMount } from 'svelte';
    import { UserService, type PosUser } from '$lib/api/users';
    import { getRoleLabel } from '$lib/app_state.svelte';
    import PermissionRow from '$lib/PermissionRow.svelte';
    import Button from '$lib/components/ui/Button.svelte';
    import Toolbar from '$lib/components/ui/Toolbar.svelte';

    // ── Constantes ──────────────────────────────────────────────────────────────
    const ROLES = [
        { value: 'admin',   label: 'Administrador' },
        { value: 'manager', label: 'Gerente' },
        { value: 'cashier', label: 'Cajero/a' },
        { value: 'waiter',  label: 'Mesero/a' },
        { value: 'kitchen', label: 'Cocina' },
    ];

    const PERMISSIONS: { key: string; label: string; desc: string }[] = [
        { key: 'can_take_orders',            label: 'Tomar pedidos',      desc: 'Crear y editar órdenes' },
        { key: 'can_send_to_kitchen',        label: 'Enviar a cocina',    desc: 'Mandar platillos a preparación' },
        { key: 'can_charge',                 label: 'Cobrar',             desc: 'Procesar pagos' },
        { key: 'can_manage_kitchen_status',  label: 'Gestionar cocina',   desc: 'Marcar platillos listos/preparando' },
        { key: 'can_view_orders',            label: 'Ver órdenes',        desc: 'Acceder al historial de órdenes' },
        { key: 'can_manage_tables',          label: 'Gestionar mesas',    desc: 'Ver y editar estado de mesas' },
        { key: 'can_view_kitchen',           label: 'Ver KDS',            desc: 'Acceso a la pantalla de cocina' },
        { key: 'can_manage_menu',            label: 'Gestionar menú',     desc: 'Editar platillos y categorías' },
        { key: 'can_manage_inventory',       label: 'Inventario',         desc: 'Gestionar ingredientes y stock' },
        { key: 'can_manage_users',           label: 'Gestionar usuarios', desc: 'Crear y editar empleados' },
        { key: 'can_manage_shifts',          label: 'Gestionar turnos',   desc: 'Abrir y cerrar caja' },
        { key: 'can_view_reports',           label: 'Ver reportes',       desc: 'Consultar estadísticas de ventas' },
    ];

    // ── Estado ───────────────────────────────────────────────────────────────
    let users = $state<PosUser[]>([]);
    let isLoading = $state(true);
    let showInactive = $state(false);
    let error = $state<string | null>(null);
    let successMsg = $state<string | null>(null);

    // Modal crear
    let showCreateModal = $state(false);
    let creating = $state(false);
    let newUser = $state({ username: '', password: '', role: 'waiter' });
    let createError = $state<string | null>(null);

    // Usuario seleccionado
    let selectedUser = $state<PosUser | null>(null);

    // Modal contraseña
    let showPwdModal = $state(false);
    let newPassword = $state('');
    let changingPwd = $state(false);

    onMount(loadUsers);

    async function loadUsers() {
        isLoading = true;
        error = null;
        try {
            users = await UserService.list(showInactive);
        } catch (e: any) {
            error = e.message;
        } finally {
            isLoading = false;
        }
    }

    async function selectUser(u: PosUser) {
        selectedUser = u;
    }

    async function handleCreate() {
        creating = true;
        createError = null;
        try {
            await UserService.create({
                username: newUser.username.trim(),
                password: newUser.password,
                role: newUser.role,
            });
            flash('✅ Usuario creado correctamente');
            showCreateModal = false;
            newUser = { username: '', password: '', role: 'waiter' };
            await loadUsers();
        } catch (e: any) {
            createError = e.message;
        } finally {
            creating = false;
        }
    }

    async function toggleActive(u: PosUser) {
        try {
            if (u.is_active) {
                await UserService.deactivate(u.uuid);
                flash('Usuario desactivado');
            } else {
                await UserService.activate(u.uuid);
                flash('Usuario activado');
            }
            await loadUsers();
            if (selectedUser?.uuid === u.uuid) {
                selectedUser = users.find(x => x.uuid === u.uuid) ?? null;
            }
        } catch (e: any) {
            error = e.message;
        }
    }

    async function changeRole(u: PosUser, newRole: string) {
        try {
            await UserService.update(u.uuid, { role: newRole });
            flash('Rol actualizado');
            await loadUsers();
            if (selectedUser?.uuid === u.uuid) {
                selectedUser = { ...selectedUser!, role: newRole };
            }
        } catch (e: any) {
            error = e.message;
        }
    }

    async function handleChangePassword() {
        if (!selectedUser || !newPassword.trim()) return;
        changingPwd = true;
        try {
            await UserService.changePassword(selectedUser.uuid, newPassword.trim());
            flash('Contraseña actualizada');
            showPwdModal = false;
            newPassword = '';
        } catch (e: any) {
            error = e.message;
        } finally {
            changingPwd = false;
        }
    }

    function flash(msg: string) {
        successMsg = msg;
        setTimeout(() => (successMsg = null), 3000);
    }

    function roleBadge(role: string) {
        const map: Record<string, string> = {
            admin: 'badge-error', manager: 'badge-warning', cashier: 'badge-info',
            waiter: 'badge-primary', kitchen: 'badge-success', operator: 'badge-error',
        };
        return map[role] ?? 'badge-ghost';
    }

    function roleIcon(role: string) {
        const icons: Record<string, string> = {
            admin: '🛡️', manager: '📊', cashier: '💵', waiter: '🍽️', kitchen: '👨‍🍳',
        };
        return icons[role] ?? '👤';
    }
</script>

<div class="p-6 flex-1 min-h-0 overflow-y-auto w-full space-y-6">

    <!-- Unified Header Toolbar -->
    <Toolbar title="Gestión de Usuarios">
        {#snippet left()}
            <a href="/admin" class="btn btn-ghost btn-sm font-black gap-1 rounded-xl uppercase tracking-wider text-xs">
                ← Volver
            </a>
            
            <div class="h-5 w-[1px] bg-base-300 mx-2"></div>
            
            <label class="label cursor-pointer gap-2 select-none">
                <span class="label-text font-bold text-xs opacity-60">Mostrar inactivos</span>
                <input type="checkbox" class="toggle toggle-xs toggle-primary" bind:checked={showInactive}
                    onchange={loadUsers} />
            </label>
        {/snippet}
        
        {#snippet right()}
            <Button id="btn-create-user" variant="primary" size="sm" class="gap-2 rounded-xl font-bold"
                onclick={() => (showCreateModal = true)}>
                <svelte:fragment slot="icon">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
                    </svg>
                </svelte:fragment>
                Nuevo Usuario
            </Button>
        {/snippet}
    </Toolbar>

    <!-- Alertas -->
    {#if successMsg}
        <div class="alert alert-success mb-4 shadow-sm">
            <span class="font-bold">{successMsg}</span>
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

        <!-- Lista de usuarios -->
        <div class="lg:col-span-1 flex flex-col gap-3">
            {#if isLoading}
                <div class="flex justify-center p-12">
                    <span class="loading loading-spinner loading-lg text-primary"></span>
                </div>
            {:else if users.length === 0}
                <div class="text-center p-8 opacity-40">
                    <p class="text-4xl mb-2">👥</p>
                    <p class="font-bold">No hay usuarios aún</p>
                    <p class="text-sm">Crea el primero con el botón de arriba</p>
                </div>
            {:else}
                {#each users as u (u.uuid)}
                    <!-- svelte-ignore a11y_click_events_have_key_events -->
                    <!-- svelte-ignore a11y_no_static_element_interactions -->
                    <div
                        class="card bg-base-100 border cursor-pointer transition-all hover:shadow-md
                            {selectedUser?.uuid === u.uuid ? 'border-primary shadow-md' : 'border-base-200'}
                            {!u.is_active ? 'opacity-50' : ''}"
                        onclick={() => selectUser(u)}
                        id="user-card-{u.uuid.slice(0,8)}"
                    >
                        <div class="card-body p-4 flex-row items-center justify-between gap-2">
                            <div class="flex items-center gap-3">
                                <div class="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-lg">
                                    {roleIcon(u.role)}
                                </div>
                                <div>
                                    <p class="font-bold leading-tight">{u.username}</p>
                                    <span class="badge badge-sm {roleBadge(u.role)} mt-1">
                                        {getRoleLabel(u.role)}
                                    </span>
                                </div>
                            </div>
                            {#if !u.is_active}
                                <span class="badge badge-ghost badge-sm shrink-0">Inactivo</span>
                            {/if}
                        </div>
                    </div>
                {/each}
            {/if}
        </div>

        <!-- Panel detalle -->
        <div class="lg:col-span-2">
            {#if selectedUser}
                <div class="card bg-base-100 border border-base-200 shadow-xl">
                    <div class="card-body">

                        <!-- Cabecera -->
                        <div class="flex items-start justify-between mb-4 pb-4 border-b border-base-200 flex-wrap gap-3">
                            <div class="flex items-center gap-4">
                                <div class="text-4xl">{roleIcon(selectedUser.role)}</div>
                                <div>
                                    <h2 class="text-2xl font-black">{selectedUser.username}</h2>
                                    <div class="flex gap-2 mt-1">
                                        <span class="badge {roleBadge(selectedUser.role)}">{getRoleLabel(selectedUser.role)}</span>
                                        {#if !selectedUser.is_active}
                                            <span class="badge badge-ghost">Inactivo</span>
                                        {/if}
                                    </div>
                                </div>
                            </div>
                            <div class="flex gap-2 flex-wrap">
                                <Button variant="outline" size="sm" onclick={() => { showPwdModal = true; }}>
                                    🔑 Contraseña
                                </Button>
                                <Button
                                    variant="outline"
                                    danger={selectedUser.is_active}
                                    success={!selectedUser.is_active}
                                    size="sm"
                                    onclick={() => toggleActive(selectedUser!)}>
                                    {selectedUser.is_active ? '🚫 Desactivar' : '✅ Activar'}
                                </Button>
                            </div>
                        </div>

                        <!-- Rol base -->
                        <div class="mb-6">
                            <h3 class="font-black text-lg mb-2">Rol base</h3>
                            <div class="flex flex-wrap gap-2">
                                {#each ROLES as r}
                                    <Button
                                        variant={selectedUser.role === r.value ? 'primary' : 'outline'}
                                        size="sm"
                                        onclick={() => changeRole(selectedUser!, r.value)}
                                        id="role-btn-{r.value}">
                                        {roleIcon(r.value)} {r.label}
                                    </Button>
                                {/each}
                            </div>
                            <p class="text-xs opacity-40 mt-2">
                                El rol define los permisos por defecto. Los overrides individuales los ajustan.
                            </p>
                        </div>

                        <!-- Permisos individuales -->
                        <div>
                            <h3 class="font-black text-lg mb-1">Permisos individuales</h3>
                            <p class="text-xs opacity-40 mb-4">
                                Los marcados en <span class="text-warning font-bold">amarillo</span> difieren del preset del rol.
                            </p>
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
                                {#each PERMISSIONS as perm (perm.key)}
                                    <PermissionRow
                                        permission={perm}
                                        userUuid={selectedUser.uuid}
                                        userRole={selectedUser.role}
                                        onFlash={flash}
                                        onError={(e) => (error = e)}
                                    />
                                {/each}
                            </div>
                        </div>

                    </div>
                </div>
            {:else}
                <div class="card bg-base-100 border border-dashed border-base-300 min-h-64 flex items-center justify-center">
                    <div class="text-center opacity-30 p-8">
                        <p class="text-5xl mb-3">👈</p>
                        <p class="font-bold text-lg">Selecciona un usuario</p>
                        <p class="text-sm">para ver y editar sus permisos</p>
                    </div>
                </div>
            {/if}
        </div>
    </div>
</div>

<!-- Modal Crear Usuario -->
{#if showCreateModal}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div class="modal modal-open z-50" onclick={() => (showCreateModal = false)}>
        <div class="modal-box" onclick={(e) => e.stopPropagation()}>
            <h3 class="font-black text-xl mb-4">➕ Nuevo Usuario</h3>
            {#if createError}
                <div class="alert alert-error mb-4 text-sm">{createError}</div>
            {/if}
            <div class="flex flex-col gap-4">
                <div class="form-control">
                    <label class="label" for="new-username">
                        <span class="label-text font-bold">Nombre de usuario</span>
                    </label>
                    <input id="new-username" type="text" class="input input-bordered"
                        placeholder="ej. juan_mesero" bind:value={newUser.username} autocomplete="off"/>
                </div>
                <div class="form-control">
                    <label class="label" for="new-password">
                        <span class="label-text font-bold">Contraseña</span>
                    </label>
                    <input id="new-password" type="password" class="input input-bordered"
                        placeholder="••••••••" bind:value={newUser.password}/>
                </div>
                <div class="form-control">
                    <label class="label" for="new-role">
                        <span class="label-text font-bold">Rol inicial</span>
                    </label>
                    <select id="new-role" class="select select-bordered" bind:value={newUser.role}>
                        {#each ROLES as r}
                            <option value={r.value}>{roleIcon(r.value)} {r.label}</option>
                        {/each}
                    </select>
                </div>
            </div>
            <div class="modal-action">
                <Button variant="ghost" onclick={() => (showCreateModal = false)}>Cancelar</Button>
                <Button id="btn-confirm-create-user" variant="primary"
                    onclick={handleCreate}
                    disabled={!newUser.username.trim() || !newUser.password.trim()}
                    isLoading={creating}>
                    Crear Usuario
                </Button>
            </div>
        </div>
    </div>
{/if}

<!-- Modal Cambiar Contraseña -->
{#if showPwdModal && selectedUser}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div class="modal modal-open z-50" onclick={() => (showPwdModal = false)}>
        <div class="modal-box" onclick={(e) => e.stopPropagation()}>
            <h3 class="font-black text-xl mb-2">🔑 Cambiar contraseña</h3>
            <p class="text-sm opacity-60 mb-4">Usuario: <strong>{selectedUser.username}</strong></p>
            <div class="form-control">
                <label class="label" for="chg-password">
                    <span class="label-text font-bold">Nueva contraseña</span>
                </label>
                <input id="chg-password" type="password" class="input input-bordered"
                    placeholder="••••••••" bind:value={newPassword}/>
            </div>
            <div class="modal-action">
                <Button variant="ghost" onclick={() => { showPwdModal = false; newPassword = ''; }}>
                    Cancelar
                </Button>
                <Button variant="warning" onclick={handleChangePassword}
                    disabled={!newPassword.trim()}
                    isLoading={changingPwd}>
                    Guardar
                </Button>
            </div>
        </div>
    </div>
{/if}
