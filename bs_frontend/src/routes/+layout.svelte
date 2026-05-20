<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { appState, setAuth, initTheme } from '$lib/app_state.svelte';
	import IntercomWidget from '$lib/components/intercom/IntercomWidget.svelte';

	let { children } = $props();

	function checkAuth() {
		if (typeof window !== 'undefined') {
			const path = page.url.pathname;
			const isPublicRoute = path.startsWith('/login') || path.startsWith('/carta');

			// Redirección básica si ya está logueado y trata de ir a login
			if (appState.isLoggedIn && path.startsWith('/login')) {
				goto('/');
			}
		}
	}

	onMount(() => {
		checkAuth();
		initTheme();
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
	{#if appState.isLoggedIn}
		<IntercomWidget />
	{/if}
</div>
