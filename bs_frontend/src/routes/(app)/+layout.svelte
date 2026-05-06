<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { appState, setTheme, setAuth, setActiveShift, initAuth, can, getRoleLabel } from '$lib/app_state.svelte';
	import { fetchApi } from '$lib/api';
	import { checkActiveShift, openShift } from '$lib/api/shifts';
	import { onMount } from 'svelte';
	import Toast from '$lib/components/Toast.svelte';
	import FloatingCart from '$lib/components/FloatingCart.svelte';
    import Button from '$lib/components/ui/Button.svelte';
	import { posSocket } from '$lib/pos_socket.svelte';
	import OpenShiftModal from '$lib/components/accounting/OpenShiftModal.svelte';
	import CloseShiftModal from '$lib/components/accounting/CloseShiftModal.svelte';
	import { setShowOpenShiftModal, setShowCloseShiftModal, setIntercomEnabled, setIntercomOpen } from '$lib/app_state.svelte';
	import IntercomWidget from '$lib/components/intercom/IntercomWidget.svelte';

	let { children } = $props();

	let isCheckingShift = $state(true);
	
	onMount(async () => {
		try {
			await initAuth();
			const res = await checkActiveShift();
			setActiveShift(res.shift);
		} catch (e) {
			console.error("Error en inicialización", e);
			goto('/login');
		} finally {
			isCheckingShift = false;
		}
	});

	async function reloadShift() {
		const res = await checkActiveShift();
		setActiveShift(res.shift);
	}

	async function handleLogout() {
		await logout();
	}



	// NavLinks — muestra todos mientras cargan los permisos, filtra una vez listos
	const ALL_NAV = [
		{ name: 'POS',        href: '/',                                  perm: 'takeOrders' },
		{ name: 'Mesas',      href: '/tables',                            perm: 'manageTables' },
		{ name: 'Órdenes',    href: '/orders',                            perm: 'viewOrders' },
		{ name: 'Inventario',  href: '/inventory',                         perm: 'manageInventory' },
		{ name: 'Cocina',     href: '/kitchen',                           perm: 'viewKitchen' },
		{ name: 'Menú',       href: '/menu',                              perm: 'manageMenu' },
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
				<div class="relative">
					<div class="w-10 h-10 bg-primary rounded-xl flex items-center justify-center text-primary-content shadow-lg shadow-primary/20 group-hover:scale-110 transition-transform duration-300">
						<span class="text-xl font-black">B</span>
					</div>
					<!-- Connection Indicator -->
					<div 
						class="absolute -top-1 -right-1 z-10" 
						title={posSocket.status === 'open' ? 'Conectado (Tiempo Real)' : posSocket.status === 'connecting' ? 'Conectando...' : 'Sin conexión'}
					>
						<span class="relative flex h-3 w-3">
							{#if posSocket.status === 'open'}
								<span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75"></span>
								<span class="relative inline-flex rounded-full h-3 w-3 bg-success shadow-sm shadow-success/40"></span>
							{:else if posSocket.status === 'connecting'}
								<span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-warning opacity-75"></span>
								<span class="relative inline-flex rounded-full h-3 w-3 bg-warning"></span>
							{:else}
								<span class="relative inline-flex rounded-full h-3 w-3 bg-error"></span>
							{/if}
						</span>
					</div>
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
			<!-- Shift Status -->
			{#if appState.isLoggedIn && can.manageShifts()}
				{#if appState.activeShift}
					<div class="hidden md:flex items-center gap-2 px-3 py-1.5 bg-success/10 text-success rounded-xl border border-success/20">
						<div class="w-1.5 h-1.5 bg-success rounded-full animate-pulse"></div>
						<span class="text-[10px] font-black uppercase tracking-widest">Turno Abierto</span>
					</div>
				{:else}
					<button 
						onclick={() => setShowOpenShiftModal(true)}
						class="hidden md:flex items-center gap-2 px-3 py-1.5 bg-warning/10 text-warning-content rounded-xl border border-warning/20 hover:bg-warning/20 transition-all cursor-pointer group"
					>
						<div class="w-1.5 h-1.5 bg-warning rounded-full group-hover:scale-125 transition-transform"></div>
						<span class="text-[10px] font-black uppercase tracking-widest">Abrir Turno</span>
					</button>
				{/if}
			{/if}



			<!-- Intercom Navbar Trigger -->
			<button 
				class="btn btn-ghost btn-circle relative {appState.intercomEnabled ? 'text-primary' : 'text-base-content/30'}"
				onclick={() => setIntercomOpen(true)}
				title="Intercom (Radio)"
			>
				<svg class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
					<path d="M16 2v4" />
					<rect x="7" y="6" width="10" height="14" rx="2" />
					<path d="M10 10h4" />
					<path d="M10 12h4" />
					<path d="M10 14h4" />
					<path d="M7 9H5v4h2" />
					<path d="M9 2v4" />
				</svg>
				{#if appState.intercomEnabled && posSocket.intercomMessages.length > 0}
					<span class="absolute top-1 right-1 flex h-3 w-3">
						<span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
						<span class="relative inline-flex rounded-full h-3 w-3 bg-primary border-2 border-base-100"></span>
					</span>
				{/if}
			</button>

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
								{#if can.viewReports() || can.manageShifts() || can.manageUsers()}
									<li><a href="/admin" class="font-black text-primary">🏠 Panel de Control</a></li>
									<div class="divider my-0 opacity-20"></div>
								{/if}

								{#if can.manageShifts()}
									<li><a href="/accounting">💵 Mi Contabilidad</a></li>
									<li><a href="/admin/registers">🖥️ Monitor de Cajas</a></li>
								{/if}

								{#if can.manageSettings()}
									<li><a href="/admin/config">⚙️ Configuración</a></li>
								{/if}
							</ul>
							<div class="py-2 border-t border-base-200">
								{#if appState.activeShift}
									<button 
										class="w-full text-left px-4 py-2 hover:bg-error/10 text-error flex items-center gap-2 transition-colors rounded-lg"
										onclick={() => { setShowCloseShiftModal(true); }}
									>
										<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
										<span class="text-xs font-black uppercase tracking-widest">Realizar Corte (Z)</span>
									</button>
								{:else if can.manageShifts()}
									<button 
										class="w-full text-left px-4 py-2 hover:bg-primary/10 text-primary flex items-center gap-2 transition-colors rounded-lg"
										onclick={() => setShowOpenShiftModal(true)}
									>
										<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
										<span class="text-xs font-black uppercase tracking-widest">Abrir Turno</span>
									</button>
								{/if}
							</div>


							<!-- Theme Selection (Quick Access) -->
							<div class="px-4 py-2 flex items-center justify-between bg-base-200/50 rounded-xl mx-2 mb-2">
								<div class="flex items-center gap-2">
									<svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.172-1.172a4 4 0 015.656 0l1.172 1.172a4 4 0 010 5.656l-1.172 1.172a4 4 0 01-5.656 0l-1.172-1.172a4 4 0 010-5.656z" /></svg>
									<span class="text-[10px] font-black uppercase tracking-widest">Tema</span>
								</div>
								<select 
									class="select select-ghost select-xs font-bold p-0 min-h-0 h-auto focus:outline-none bg-transparent" 
									onchange={(e) => setTheme(e.currentTarget.value)} 
									value={appState.currentTheme}
								>
									{#each ['corporate', 'coffee', 'bumblebee', 'light', 'dark', 'dim'] as theme}
										<option value={theme}>{theme}</option>
									{/each}
								</select>
							</div>

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
	<main class="flex-1 flex flex-col min-h-0 relative overflow-y-auto elegant-scroll">
		{#if !appState.permissionsLoaded}
			<div class="absolute inset-0 flex items-center justify-center bg-base-100/50 backdrop-blur-sm z-50">
				<span class="loading loading-spinner loading-lg text-primary"></span>
			</div>
		{:else}
			{@render children()}
		{/if}
	</main>
	
	<!-- Subtle Gradient for Depth (Optional) -->
	<div class="fixed bottom-0 left-0 w-full h-32 bg-gradient-to-t from-base-200/50 to-transparent pointer-events-none"></div>

	<!-- Open Shift Modal (Triggered) -->
	{#if appState.showOpenShiftModal}
	    <OpenShiftModal />
	{/if}

	<!-- Close Shift Modal (Global) -->
	{#if appState.showCloseShiftModal && appState.activeShift}
		<CloseShiftModal 
			shift={appState.activeShift} 
			onClose={() => { setShowCloseShiftModal(false); reloadShift(); }} 
		/>
	{/if}
	
	{#if appState.isLoggedIn && can.takeOrders?.()}
		<FloatingCart />
	{/if}
	<IntercomWidget />
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
