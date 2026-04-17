<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { appState, setTheme, setAuth, setActiveShift, initAuth, can, getRoleLabel } from '$lib/app_state.svelte';
	import { checkActiveShift, openShift } from '$lib/api/shifts';
	import { onMount } from 'svelte';
	import Toast from '$lib/components/Toast.svelte';
	import FloatingCart from '$lib/components/FloatingCart.svelte';
    import Button from '$lib/components/ui/Button.svelte';

	let { children } = $props();

	let isCheckingShift = $state(true);
	let initialCash = $state(0);
	let isOpeningShift = $state(false);
	
	onMount(async () => {
		const token = typeof localStorage !== 'undefined' ? localStorage.getItem('X-Omni-Token') : null;
		if (!token) {
			goto('/login');
			return;
		}
		try {
			await initAuth();
			const res = await checkActiveShift();
			setActiveShift(res.shift);
		} catch (e) {
			console.error("Error en inicialización", e);
		} finally {
			isCheckingShift = false;
		}
	});

	async function handleOpenShift() {
		isOpeningShift = true;
		try {
			const shift = await openShift(initialCash);
			setActiveShift(shift);
		} catch (e) {
			alert("Error al abrir turno: " + e);
		} finally {
			isOpeningShift = false;
		}
	}

	function handleLogout() {
		localStorage.removeItem('X-Omni-Token');
		setAuth(false);
		goto('/login');
	}

	function changeTheme(event: Event) {
		const select = event.target as HTMLSelectElement;
		setTheme(select.value);
	}

	// NavLinks — muestra todos mientras cargan los permisos, filtra una vez listos
	const ALL_NAV = [
		{ name: 'POS',        href: '/',                                  perm: 'takeOrders' },
		{ name: 'Mesas',      href: '/tables',                            perm: 'manageTables' },
		{ name: 'Órdenes',    href: '/orders',                            perm: 'viewOrders' },
		{ name: 'Cocina',     href: '/kitchen',                           perm: 'viewKitchen' },
		{ name: 'Menú',       href: '/menu',                              perm: 'manageMenu' },
		{ name: 'Inventario', href: '/admin/inventory/ingredients',       perm: 'manageInventory' },
	] as const;

	type PermKey = keyof typeof can;

	let navLinks = $derived(
		// Si está logueado pero no hay permisos (por algún edge case), mostrar todo
		(appState.isLoggedIn && Object.keys(appState.permissions).length === 0)
			? [...ALL_NAV]
			: ALL_NAV.filter(l => can[l.perm as PermKey]?.())
	);

	function isActive(href: string) {
		if (href === '/' && page.url.pathname === '/') return true;
		if (href !== '/' && page.url.pathname.startsWith(href)) return true;
		return false;
	}
</script>

<div class="h-screen flex flex-col bg-base-200 overflow-hidden">
	<!-- Navbar Premium -->
	<header class="navbar bg-base-100 border-b border-base-200 sticky top-0 z-30 shadow-sm px-4 lg:px-8 h-20">
		<div class="navbar-start gap-4">
			<!-- Mobile Menu Button -->
			<div class="dropdown lg:hidden">
				<label tabindex="0" class="btn btn-ghost btn-circle">
					<svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h7" /></svg>
				</label>
				<ul tabindex="0" class="menu menu-sm dropdown-content mt-3 z-[1] p-2 shadow bg-base-100 rounded-box w-52 border border-base-300">
					{#each navLinks as link}
						<li><a href={link.href} class={isActive(link.href) ? 'active font-bold' : ''}>{link.name}</a></li>
					{/each}
				</ul>
			</div>

			<a href="/" class="flex items-center gap-3 group">
				<div class="w-10 h-10 bg-primary rounded-xl flex items-center justify-center text-primary-content shadow-lg shadow-primary/20 group-hover:scale-110 transition-transform duration-300">
					<span class="text-xl font-black">B</span>
				</div>
				<span class="text-2xl font-black tracking-tighter text-base-content hidden sm:inline-block">Black<span class="text-primary">Shot</span></span>
			</a>

			<div class="hidden lg:flex items-center gap-1 ml-8">
				{#each navLinks as link}
					<a 
						href={link.href} 
						class="btn btn-ghost btn-md font-bold px-4 rounded-xl transition-all duration-200 hover:bg-primary/10 hover:text-primary {isActive(link.href) ? 'bg-primary/5 text-primary border-b-2 border-primary rounded-b-none' : 'opacity-80'} {link.name === 'Caja' ? 'text-secondary font-black bg-secondary/10' : ''}"
					>
						{link.name}
					</a>
				{/each}
			</div>
		</div>

		<div class="navbar-end gap-3">
			<div class="hidden lg:flex items-center gap-2 mr-4 text-xs font-bold opacity-50 uppercase tracking-widest bg-base-200 px-3 py-1 rounded-lg">
				Tema: 
				<select class="select select-ghost select-xs font-bold p-0 min-h-0 h-auto focus:outline-none" onchange={changeTheme} value={appState.currentTheme}>
					{#each ['corporate', 'coffee', 'bumblebee', 'light', 'dark', 'dim'] as theme}
						<option value={theme}>{theme}</option>
					{/each}
				</select>
			</div>

			{#if appState.isLoggedIn}
				<div class="dropdown dropdown-end">
					<label tabindex="0" class="btn btn-ghost btn-circle avatar border-2 border-primary/20">
						<div class="w-10 rounded-full">
							<img src="https://api.dicebear.com/7.x/avataaars/svg?seed={appState.userName ?? 'Admin'}" alt="Avatar" />
						</div>
					</label>
					<div tabindex="0" class="mt-3 z-[1] card card-compact dropdown-content w-64 bg-base-100 shadow-xl border border-base-300">
						<div class="card-body">
							<div class="flex flex-col gap-1 pb-2 border-b border-base-200">
								<span class="font-black text-lg">{appState.userName ?? 'Usuario'}</span>
								<span class="text-xs opacity-50 uppercase tracking-widest">{getRoleLabel(appState.userRole)}</span>
							</div>
							<ul class="menu p-0">
								{#if can.manageUsers()}
									<li><a href="/admin/users" id="nav-usuarios">👥 Usuarios</a></li>
								{/if}
								{#if can.manageShifts()}
									<li><a href="/admin/corte">💵 Realizar Corte</a></li>
								{/if}
								{#if can.manageSettings()}
									<li><a href="/admin/config">⚙️ Configuración</a></li>
								{/if}
								{#if can.viewReports()}
									<li><a href="/admin/analytics">📈 Analíticas</a></li>
								{/if}
								{#if can.viewAudits()}
									<li><a href="/admin/audits">🛡️ Auditoría</a></li>
								{/if}
							</ul>
							<div class="card-actions pt-2 border-t border-base-200">
								<Button variant="danger" size="sm" class="btn-block" onclick={handleLogout}>Cerrar Sesión</Button>
							</div>
						</div>
					</div>
				</div>
			{:else}
				<Button variant="primary" size="sm" class="font-bold" onclick={() => goto('/login')}>Acceder</Button>
			{/if}
		</div>
	</header>

	<!-- Main Content Area -->
	<main class="flex-1 flex flex-col min-h-0 relative">
		{@render children()}
	</main>
	
	<!-- Subtle Gradient for Depth (Optional) -->
	<div class="fixed bottom-0 left-0 w-full h-32 bg-gradient-to-t from-base-200/50 to-transparent pointer-events-none"></div>

	<!-- Open Shift Modal (Blocking) -->
	{#if !isCheckingShift && !appState.activeShift}
	<div class="modal modal-open bg-base-300/80 backdrop-blur-sm z-50">
		<div class="modal-box shadow-2xl border border-base-content/10">
			<h3 class="font-black text-2xl text-primary flex items-center gap-2 mb-2">
				<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-8 h-8">
					<path stroke-linecap="round" stroke-linejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
				</svg>
				Apertura de Caja
			</h3>
			<p class="py-2 text-base-content/80 font-medium">No hay un turno activo. Para registrar ventas, necesitas iniciar la caja indicando el fondo inicial con el que cuentas.</p>
			
			<div class="form-control w-full mt-4">
				<label class="label">
					<span class="label-text font-bold">Fondo de Caja (Efectivo Inicial)</span>
				</label>
				<div class="join w-full shadow-sm">
					<span class="join-item btn btn-active pointer-events-none font-black text-lg bg-base-200 border-base-300 text-base-content/50">$</span>
					<input type="number" step="0.01" min="0" bind:value={initialCash} placeholder="0.00" class="input input-bordered join-item w-full text-lg font-bold text-right" />
				</div>
			</div>

			<div class="modal-action mt-6 flex gap-3">
				<Button 
                    variant="primary" 
                    size="lg" 
                    class="btn-block font-bold" 
                    onclick={handleOpenShift} 
                    disabled={initialCash < 0}
                    {isLoading}
                >
					Abrir Turno de Caja
				</Button>
			</div>
		</div>
	</div>
	{/if}
	
	{#if appState.isLoggedIn && can.takeOrders?.()}
		<FloatingCart />
	{/if}
	<Toast />
</div>

<style>
	:global(body) {
		overflow: hidden;
	}
	
	/* Smooth transitions for links */
	.btn {
		transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
	}
</style>
