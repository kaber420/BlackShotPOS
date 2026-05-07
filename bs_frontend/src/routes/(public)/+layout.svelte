<script lang="ts">
    import { appState, setTheme } from '$lib/app_state.svelte';
    import { onMount } from 'svelte';

    let { children } = $props();

    function changeTheme(event: Event) {
        const select = event.target as HTMLSelectElement;
        setTheme(select.value);
    }

    onMount(() => {
        // Default to a premium theme for public view if not set
        if (!appState.currentTheme) {
            setTheme('corporate');
        }
    });
</script>

<div class="min-h-screen bg-base-100 flex flex-col font-sans selection:bg-primary/30" style="--menu-accent: {appState.settings?.menu_accent_color || '#6366f1'}">
    <!-- Header Premium -->
    <header class="sticky top-0 z-50 bg-base-100/80 backdrop-blur-xl border-b border-base-200">
        <div class="max-w-7xl mx-auto px-4 h-20 flex items-center justify-between font-outfit">
            <div class="flex items-center gap-3">
                {#if appState.settings?.menu_logo_url}
                    <img src={appState.settings.menu_logo_url} alt="Logo" class="h-10 w-auto object-contain" />
                {:else}
                    <div class="w-10 h-10 bg-primary rounded-xl flex items-center justify-center text-primary-content shadow-lg shadow-primary/20" style="background-color: var(--menu-accent)">
                        <span class="text-xl font-black">{appState.settings?.name?.[0] || 'B'}</span>
                    </div>
                {/if}
                <div class="flex flex-col leading-none">
                    <span class="text-2xl font-black tracking-tighter text-base-content">
                        {appState.settings?.name?.split(' ')[0] || 'Black'}<span class="text-primary" style="color: var(--menu-accent)">{appState.settings?.name?.split(' ').slice(1).join(' ') || 'Shot'}</span>
                    </span>
                    <span class="text-[10px] uppercase tracking-[0.2em] font-bold opacity-40">Digital Menu</span>
                </div>
            </div>

            <div class="flex items-center gap-4">
                <div class="hidden sm:flex items-center gap-2 text-[10px] font-bold opacity-50 uppercase tracking-widest bg-base-200 px-3 py-1.5 rounded-lg border border-base-300">
                    Theme:
                    <select class="select select-ghost select-xs font-bold p-0 min-h-0 h-auto focus:outline-none bg-transparent" onchange={changeTheme} value={appState.currentTheme}>
                        {#each ['corporate', 'coffee', 'bumblebee', 'light', 'dark', 'dim'] as theme}
                            <option value={theme}>{theme}</option>
                        {/each}
                    </select>
                </div>
            </div>
        </div>
    </header>

    <!-- Content -->
    <main class="flex-1">
        {@render children()}
    </main>

    <!-- Footer Moderno & Rediseñado (Más compacto) -->
    <footer class="bg-base-200 pt-12 pb-8 px-4 mt-10 border-t border-base-300">
        <div class="max-w-7xl mx-auto flex flex-col items-center text-center gap-6">
            <!-- Branding (Simplificado sin el logo de la 'B' que molestaba) -->
            <div class="flex flex-col items-center gap-2">
                {#if appState.settings?.menu_logo_url}
                    <img src={appState.settings.menu_logo_url} alt="Logo" class="h-12 w-auto opacity-80 mb-4" />
                {/if}
                <div>
                    <h3 class="text-3xl font-black uppercase tracking-tighter">
                        {appState.settings?.menu_footer_text || 'BlackShot POS'}
                    </h3>
                    <p class="text-[10px] uppercase tracking-[0.3em] font-bold opacity-30 mt-1">
                        {appState.settings?.menu_footer_tagline || 'Disfruta de nuestra selección premium.'}
                    </p>
                </div>
            </div>

            <!-- Social Links -->
            <div class="flex flex-wrap justify-center gap-4">
                {#if appState.settings?.menu_facebook_url}
                    <a href={appState.settings.menu_facebook_url} target="_blank" rel="noopener noreferrer" class="w-12 h-12 flex items-center justify-center rounded-2xl bg-base-100 hover:bg-blue-600 hover:text-white transition-all shadow-sm group">
                        <svg class="w-6 h-6 fill-current" viewBox="0 0 24 24"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>
                    </a>
                {/if}
                {#if appState.settings?.menu_instagram_url}
                    <a href={appState.settings.menu_instagram_url} target="_blank" rel="noopener noreferrer" class="w-12 h-12 flex items-center justify-center rounded-2xl bg-base-100 hover:bg-gradient-to-tr from-yellow-400 via-red-500 to-purple-600 hover:text-white transition-all shadow-sm">
                        <svg class="w-6 h-6 fill-current" viewBox="0 0 24 24"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/></svg>
                    </a>
                {/if}
                {#if appState.settings?.menu_youtube_url}
                    <a href={appState.settings.menu_youtube_url} target="_blank" rel="noopener noreferrer" class="w-12 h-12 flex items-center justify-center rounded-2xl bg-base-100 hover:bg-red-600 hover:text-white transition-all shadow-sm">
                        <svg class="w-6 h-6 fill-current" viewBox="0 0 24 24"><path d="M19.615 3.184c-3.604-.246-11.631-.245-15.23 0-3.897.266-4.356 2.62-4.385 8.816.029 6.185.484 8.549 4.385 8.816 3.6.245 11.626.246 15.23 0 3.897-.266 4.356-2.62 4.385-8.816-.029-6.185-.484-8.549-4.385-8.816zm-10.615 12.816v-8l8 4-8 4z"/></svg>
                    </a>
                {/if}
                {#if appState.settings?.menu_twitter_url}
                    <a href={appState.settings.menu_twitter_url} target="_blank" rel="noopener noreferrer" class="w-12 h-12 flex items-center justify-center rounded-2xl bg-base-100 hover:bg-black hover:text-white transition-all shadow-sm">
                        <svg class="w-5 h-5 fill-current" viewBox="0 0 24 24"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
                    </a>
                {/if}
                {#if appState.settings?.menu_tiktok_url}
                    <a href={appState.settings.menu_tiktok_url} target="_blank" rel="noopener noreferrer" class="w-12 h-12 flex items-center justify-center rounded-2xl bg-base-100 hover:bg-[#000000] hover:text-white transition-all shadow-sm">
                        <svg class="w-5 h-5 fill-current" viewBox="0 0 24 24"><path d="M12.525.02c1.31-.032 2.612.019 3.887.155a8.21 8.21 0 0 0 0 2.25c.01 2.316 1.4 4.322 3.42 5.176.012.893.01 1.787.01 2.68a12.083 12.083 0 0 1-5.122-1.728l-.01 7.24a5.83 5.83 0 1 1-5.83-5.834 5.768 5.768 0 0 1 1.638.238l.011-3.003A8.834 8.834 0 1 0 12.525.02z"/></svg>
                    </a>
                {/if}
                {#if appState.settings?.menu_whatsapp_url}
                    <a href={appState.settings.menu_whatsapp_url} target="_blank" rel="noopener noreferrer" class="w-12 h-12 flex items-center justify-center rounded-2xl bg-base-100 hover:bg-green-500 hover:text-white transition-all shadow-sm">
                        <svg class="w-6 h-6 fill-current" viewBox="0 0 24 24"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 0 1-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 0 1-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 0 1 2.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0 0 12.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 0 0 5.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 0 0-3.48-8.413Z"/></svg>
                    </a>
                {/if}
            </div>

            <div class="h-px w-full max-w-sm bg-gradient-to-r from-transparent via-base-content/10 to-transparent"></div>

            <!-- Credits (Unificados y sutiles) -->
            <p class="text-[9px] font-black uppercase tracking-[0.4em] opacity-20">
                © {new Date().getFullYear()} — {appState.settings?.name || 'BlackShot'} — Todos los derechos reservados
            </p>
        </div>
    </footer>
</div>

<style>
    :global(html) {
        scroll-behavior: smooth;
    }
    
    .font-outfit {
        font-family: 'Outfit', 'Inter', system-ui, sans-serif;
    }
</style>
