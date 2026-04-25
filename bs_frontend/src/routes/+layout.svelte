<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { appState, setAuth } from '$lib/app_state.svelte';

	let { children } = $props();

	function checkAuth() {
		if (typeof window !== 'undefined') {
			const token = localStorage.getItem('X-Omni-Token');
			setAuth(!!token);

			const path = page.url.pathname;
			const isPublicRoute = path.startsWith('/login') || path.startsWith('/carta');

			// Redirección si no está logueado
			if (!appState.isLoggedIn && !isPublicRoute) {
				goto('/login');
			}
			// Redirección si ya está logueado y trata de ir a login
			else if (appState.isLoggedIn && path.startsWith('/login')) {
				goto('/');
			}
		}
	}

	onMount(() => {
		checkAuth();
		// Escuchar cambios en localStorage (otro tab cerró sesión, etc.)
		window.addEventListener('storage', checkAuth);
		return () => window.removeEventListener('storage', checkAuth);
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<meta name="theme-color" content="#ffffff" />
</svelte:head>

<div data-theme={appState.currentTheme}>
	{@render children()}
</div>
