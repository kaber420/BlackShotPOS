<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	
	let { children } = $props();
	let hasToken = $state(false);

	$effect(() => {
		// Triggers reactively on path change
		const path = $page.url.pathname;
		if (typeof window !== 'undefined') {
			hasToken = !!localStorage.getItem('customer_token');
		}
	});
</script>

<svelte:head>
	<title>BlackShot Customer Portal</title>
</svelte:head>

<div class="min-h-screen bg-base-100 flex flex-col font-sans selection:bg-primary/30">
    <header class="sticky top-0 z-50 bg-base-100/80 backdrop-blur-xl border-b border-base-200">
        <div class="max-w-7xl mx-auto px-4 h-20 flex items-center justify-between">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 bg-primary rounded-xl flex items-center justify-center text-primary-content shadow-lg shadow-primary/20">
                    <span class="text-xl font-black">B</span>
                </div>
                <div class="flex flex-col leading-none">
                    <span class="text-2xl font-black tracking-tighter text-base-content">
                        Black<span class="text-primary">Shot</span>
                    </span>
                    <span class="text-[10px] uppercase tracking-[0.2em] font-bold opacity-40">Portal de Clientes</span>
                </div>
            </div>

            {#if hasToken && $page.url.pathname !== '/login'}
                {#if $page.url.pathname === '/perfil'}
                    <a 
                        href="/menu"
                        class="btn btn-neutral rounded-2xl flex items-center gap-2 font-black uppercase text-[10px] tracking-wider shadow-lg transition-all duration-300 hover:scale-105 active:scale-95"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16" />
                        </svg>
                        Ver Menú
                    </a>
                {:else}
                    <a 
                        href="/perfil"
                        class="btn btn-primary rounded-2xl flex items-center gap-2 font-black uppercase text-[10px] tracking-wider shadow-lg shadow-primary/15 transition-all duration-300 hover:scale-105 active:scale-95"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                        Mi Perfil / Monedero
                    </a>
                {/if}
            {/if}
        </div>
    </header>

    <main class="flex-1">
        {@render children()}
    </main>

    <footer class="bg-base-200 pt-12 pb-8 px-4 mt-10 border-t border-base-300">
        <div class="max-w-7xl mx-auto flex flex-col items-center text-center gap-6">
            <div class="flex flex-col items-center gap-2">
                <div>
                    <h3 class="text-3xl font-black uppercase tracking-tighter">
                        BlackShot POS
                    </h3>
                    <p class="text-[10px] uppercase tracking-[0.3em] font-bold opacity-30 mt-1">
                        Disfruta de nuestra selección premium.
                    </p>
                </div>
            </div>
            <div class="h-px w-full max-w-sm bg-gradient-to-r from-transparent via-base-content/10 to-transparent"></div>
            <p class="text-[9px] font-black uppercase tracking-[0.4em] opacity-20">
                © {new Date().getFullYear()} — BlackShot — Todos los derechos reservados
            </p>
        </div>
    </footer>
</div>

<style>
    :global(html) {
        scroll-behavior: smooth;
    }
</style>
