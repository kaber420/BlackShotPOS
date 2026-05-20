<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { appState, setTheme, setAuth, setActiveShift, initAuth, can, getRoleLabel, logout } from '$lib/app_state.svelte';
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

	// --- AVATAR Y PERSONALIZACIÓN PREMIUM (OFFLINE-FIRST) ---
	function getInitials(name: string | null): string {
		if (!name) return '??';
		const clean = name.trim();
		if (clean.length === 0) return '??';
		const parts = clean.split(/[\s_-]+/);
		if (parts.length >= 2) {
			return (parts[0][0] + parts[1][0]).toUpperCase();
		}
		return clean.slice(0, 2).toUpperCase();
	}

	const AVATAR_GRADIENTS = [
		{ id: 'purple', classes: 'from-violet-500 to-indigo-500' },
		{ id: 'emerald', classes: 'from-emerald-500 to-teal-500' },
		{ id: 'rose', classes: 'from-pink-500 to-rose-500' },
		{ id: 'amber', classes: 'from-amber-500 to-orange-500' },
		{ id: 'blue', classes: 'from-blue-500 to-cyan-500' },
		{ id: 'magenta', classes: 'from-fuchsia-500 to-pink-600' },
	];

	let customAvatarImg = $state<string | null>(null);
	let selectedAvatarStyle = $state<string>('');
	let fileInput = $state<HTMLInputElement | null>(null);

	$effect(() => {
		if (typeof localStorage !== 'undefined' && appState.userName) {
			customAvatarImg = localStorage.getItem(`bs_avatar_img_${appState.userName}`) || null;
			selectedAvatarStyle = localStorage.getItem(`bs_avatar_style_${appState.userName}`) || '';
		} else {
			customAvatarImg = null;
			selectedAvatarStyle = '';
		}
	});

	function getAvatarColor(name: string | null): string {
		if (selectedAvatarStyle) {
			const found = AVATAR_GRADIENTS.find(g => g.id === selectedAvatarStyle);
			if (found) return found.classes;
		}
		if (!name) return 'from-primary to-primary-focus';
		let hash = 0;
		for (let i = 0; i < name.length; i++) {
			hash = name.charCodeAt(i) + ((hash << 5) - hash);
		}
		const index = Math.abs(hash) % AVATAR_GRADIENTS.length;
		return AVATAR_GRADIENTS[index].classes;
	}

	function setAvatarColor(colorId: string) {
		if (!appState.userName) return;
		selectedAvatarStyle = colorId;
		if (typeof localStorage !== 'undefined') {
			localStorage.setItem(`bs_avatar_style_${appState.userName}`, colorId);
		}
	}

	function handleAvatarUpload(event: Event) {
		const input = event.target as HTMLInputElement;
		if (!input.files || input.files.length === 0) return;
		
		const file = input.files[0];
		const reader = new FileReader();
		
		reader.onload = (e) => {
			const img = new Image();
			img.onload = () => {
				const canvas = document.createElement('canvas');
				const MAX_WIDTH = 128;
				const MAX_HEIGHT = 128;
				let width = img.width;
				let height = img.height;

				if (width > height) {
					if (width > MAX_WIDTH) {
						height *= MAX_WIDTH / width;
						width = MAX_WIDTH;
					}
				} else {
					if (height > MAX_HEIGHT) {
						width *= MAX_HEIGHT / height;
						height = MAX_HEIGHT;
					}
				}

				canvas.width = width;
				canvas.height = height;
				const ctx = canvas.getContext('2d');
				ctx?.drawImage(img, 0, 0, width, height);

				const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
				customAvatarImg = dataUrl;
				if (typeof localStorage !== 'undefined' && appState.userName) {
					localStorage.setItem(`bs_avatar_img_${appState.userName}`, dataUrl);
				}
			};
			img.src = e.target?.result as string;
		};
		reader.readAsDataURL(file);
	}

	function removeCustomAvatar() {
		customAvatarImg = null;
		if (typeof localStorage !== 'undefined' && appState.userName) {
			localStorage.removeItem(`bs_avatar_img_${appState.userName}`);
		}
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
					<!-- File Input for local offline avatar upload -->
					<input 
						type="file" 
						accept="image/*" 
						class="hidden" 
						onchange={handleAvatarUpload} 
						bind:this={fileInput}
					/>

					<!-- Sleek Minimalist Avatar (No bulky text in Navbar) -->
					<label tabindex="0" class="btn btn-ghost btn-circle avatar border-2 border-primary/20 hover:border-primary hover:scale-105 transition-all duration-300 shadow-sm cursor-pointer select-none">
						<div class="w-10 h-10 rounded-full overflow-hidden flex items-center justify-center">
							{#if customAvatarImg}
								<img src={customAvatarImg} alt="User Avatar" class="w-full h-full object-cover" />
							{:else}
								<div class="w-full h-full bg-gradient-to-tr {getAvatarColor(appState.userName)} text-white flex items-center justify-center font-black text-sm tracking-wider">
									{getInitials(appState.userName ?? 'Admin')}
								</div>
							{/if}
						</div>
					</label>

					<!-- Beautiful Premium Dropdown Card -->
					<div tabindex="0" class="mt-3 z-[1] card card-compact dropdown-content w-72 bg-base-100 shadow-xl border border-base-300 overflow-hidden">
						<!-- Custom Header Gradient representing the role/style -->
						<div class="h-16 bg-gradient-to-r {getAvatarColor(appState.userName)} opacity-85 relative">
							<!-- Subtle overlay -->
							<div class="absolute inset-0 bg-black/10"></div>
						</div>

						<div class="card-body -mt-10 relative pt-0 px-4 pb-4">
							<!-- Large avatar inside card to show profile look -->
							<div class="flex items-end justify-between mb-2">
								<div class="avatar placeholder">
									<div class="w-16 h-16 rounded-2xl border-4 border-base-100 shadow-md bg-gradient-to-tr {getAvatarColor(appState.userName)} overflow-hidden flex items-center justify-center">
										{#if customAvatarImg}
											<img src={customAvatarImg} alt="Avatar" class="w-full h-full object-cover" />
										{:else}
											<span class="text-white font-black text-xl">{getInitials(appState.userName ?? 'Admin')}</span>
										{/if}
									</div>
								</div>
								
								<!-- Role Badge -->
								<span class="badge badge-sm uppercase tracking-widest font-black py-2.5 px-3 bg-base-200 border-base-300 text-base-content/85 -mb-2">
									{getRoleLabel(appState.userRole)}
								</span>
							</div>

							<!-- User Details -->
							<div class="flex flex-col gap-0.5 pb-2">
								<span class="font-black text-lg text-base-content leading-tight">{appState.userName ?? 'Usuario'}</span>
								<span class="text-[9px] opacity-45 uppercase tracking-wider font-extrabold">Sesión Activa</span>
							</div>

							<!-- Personalización de Avatar (Premium & Compact) -->
							<div class="py-2.5 flex flex-col gap-2 bg-base-200/50 rounded-xl px-2.5 border border-base-200/60 my-1">
								<span class="text-[9px] font-black uppercase tracking-wider text-base-content/65">Estilo Personal</span>
								
								<div class="flex items-center justify-between gap-1.5 mt-0.5">
									{#if customAvatarImg}
										<button 
											type="button"
											onclick={removeCustomAvatar}
											class="btn btn-xs btn-error btn-outline font-black rounded-lg text-[8px] uppercase tracking-widest cursor-pointer py-1"
										>
											🗑️ Quitar Foto
										</button>
									{:else}
										<button 
											type="button"
											onclick={() => fileInput?.click()}
											class="btn btn-xs btn-primary btn-outline font-black rounded-lg text-[8px] uppercase tracking-widest cursor-pointer py-1"
										>
											📸 Subir Foto
										</button>
									{/if}

									<!-- Color Swatches -->
									<div class="flex gap-1">
										{#each AVATAR_GRADIENTS as g}
											<button 
												type="button"
												onclick={() => setAvatarColor(g.id)}
												class="w-4 h-4 rounded-full bg-gradient-to-tr {g.classes} cursor-pointer border transition-all duration-150 hover:scale-110 active:scale-90 {selectedAvatarStyle === g.id ? 'ring-1 ring-primary ring-offset-0.5 border-white' : 'border-base-300'}"
												title="Elegir gradiente {g.id}"
											></button>
										{/each}
									</div>
								</div>
							</div>

							<ul class="menu p-0 mt-1">
								{#if can.viewReports() || can.manageShifts() || can.manageUsers()}
									<li><a href="/admin" class="font-black text-primary">🏠 Panel de Control</a></li>
									<div class="divider my-0 opacity-20"></div>
								{/if}

								{#if can.manageShifts()}
									<li><a href="/accounting">💵 Mi Caja</a></li>
								{/if}

								{#if can.manageSettings()}
									<li><a href="/admin/config">⚙️ Configuración</a></li>
								{/if}
							</ul>

							<div class="py-1.5 border-t border-base-200 mt-1">
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

							<!-- Theme Selection Swatches -->
							<div class="px-2.5 py-2 flex flex-col gap-1.5 bg-base-200/50 rounded-xl border border-base-200/60 mt-1 mb-1">
								<div class="flex items-center justify-between">
									<div class="flex items-center gap-1">
										<span class="text-[9px] font-black uppercase tracking-wider text-base-content/75">Tema Visual</span>
									</div>
									<span class="text-[8px] font-black px-1 py-0.5 bg-primary/10 text-primary rounded uppercase tracking-wider">
										{appState.currentTheme}
									</span>
								</div>
								
								<div class="grid grid-cols-3 gap-1 mt-0.5">
									{#each [
										{ id: 'corporate', name: 'Corp', bg: 'bg-white', primary: 'bg-[#4b6bfb]', border: 'border-slate-200' },
										{ id: 'coffee', name: 'Café', bg: 'bg-[#20161F]', primary: 'bg-[#DB924B]', border: 'border-[#181017]' },
										{ id: 'bumblebee', name: 'Avispa', bg: 'bg-white', primary: 'bg-[#E0A82E]', border: 'border-slate-200' },
										{ id: 'light', name: 'Claro', bg: 'bg-white', primary: 'bg-[#570DF8]', border: 'border-slate-200' },
										{ id: 'dark', name: 'Oscuro', bg: 'bg-[#1D232A]', primary: 'bg-[#7480FF]', border: 'border-[#15191E]' },
										{ id: 'dim', name: 'Ocaso', bg: 'bg-[#2A303C]', primary: 'bg-[#661AE6]', border: 'border-[#1F242E]' }
									] as t}
										<button 
											type="button"
											onclick={() => setTheme(t.id)}
											class="flex flex-col items-center justify-center p-1 rounded-lg border transition-all duration-200 relative group cursor-pointer overflow-hidden {appState.currentTheme === t.id ? 'border-primary ring-1 ring-primary/20 bg-base-100 shadow-sm' : 'border-base-300 hover:border-base-content/20 bg-base-100/50'}"
											title={t.id}
										>
											<div class="flex gap-0.5 mb-0.5 items-center justify-center">
												<span class="w-2.5 h-2.5 rounded-full {t.bg} {t.border} border shadow-xs inline-block"></span>
												<span class="w-2.5 h-2.5 rounded-full {t.primary} shadow-xs inline-block"></span>
											</div>
											<span class="text-[8px] font-black tracking-tighter text-base-content/80 group-hover:text-base-content uppercase">
												{t.name}
											</span>
											{#if appState.currentTheme === t.id}
												<span class="absolute top-0.5 right-0.5 w-1 h-1 bg-primary rounded-full"></span>
											{/if}
										</button>
									{/each}
								</div>
							</div>

							<div class="card-actions pt-1.5 border-t border-base-200">
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
