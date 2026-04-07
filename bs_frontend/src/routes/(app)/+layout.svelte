<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { appState, setTheme, setAuth } from '$lib/app_state.svelte';

	let { children } = $props();

	function handleLogout() {
		localStorage.removeItem('X-Omni-Token');
		setAuth(false);
		goto('/login');
	}

	function changeTheme(event: Event) {
		const select = event.target as HTMLSelectElement;
		setTheme(select.value);
	}

	const navLinks = [
		{ name: 'POS', href: '/', icon: 'POS' },
		{ name: 'Mesas', href: '/tables', icon: 'M' },
		{ name: 'Órdenes', href: '/orders', icon: 'O' },
		{ name: 'Inventario', href: '/admin/inventory/ingredients', icon: 'I' },
		{ name: 'Cocina', href: '/kitchen', icon: 'C' },
		{ name: 'Menú', href: '/menu', icon: 'M' }
	];

	function isActive(href: string) {
		if (href === '/' && page.url.pathname === '/') return true;
		if (href !== '/' && page.url.pathname.startsWith(href)) return true;
		return false;
	}
</script>

<div class="min-h-screen flex flex-col bg-base-200">
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
					<div class="divider"></div>
					<li><a href="/admin/corte" class="text-error font-semibold">Corte de Caja</a></li>
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
						class="btn btn-ghost btn-md font-bold px-4 rounded-xl transition-all duration-200 hover:bg-primary/10 hover:text-primary {isActive(link.href) ? 'bg-primary/5 text-primary border-b-2 border-primary rounded-b-none' : 'opacity-80'}"
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
							<img src="https://api.dicebear.com/7.x/avataaars/svg?seed=Admin" alt="Admin" />
						</div>
					</label>
					<div tabindex="0" class="mt-3 z-[1] card card-compact dropdown-content w-64 bg-base-100 shadow-xl border border-base-300">
						<div class="card-body">
							<div class="flex flex-col gap-1 pb-2 border-b border-base-200">
								<span class="font-black text-lg">Administrador</span>
								<span class="text-xs opacity-50">admin@blackshot.pos</span>
							</div>
							<ul class="menu p-0">
								<li><a href="/admin">Panel Admin</a></li>
								<li><a href="/admin/corte">Realizar Corte</a></li>
								<li><a>Configuración</a></li>
							</ul>
							<div class="card-actions pt-2 border-t border-base-200">
								<button class="btn btn-error btn-sm btn-block text-white" onclick={handleLogout}>Cerrar Sesión</button>
							</div>
						</div>
					</div>
				</div>
			{:else}
				<a href="/login" class="btn btn-primary btn-sm rounded-xl font-bold shadow-lg shadow-primary/20">Acceder</a>
			{/if}
		</div>
	</header>

	<!-- Main Content Area -->
	<main class="flex-1 overflow-y-auto relative">
		{@render children()}
	</main>
	
	<!-- Subtle Gradient for Depth (Optional) -->
	<div class="fixed bottom-0 left-0 w-full h-32 bg-gradient-to-t from-base-200/50 to-transparent pointer-events-none"></div>
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
