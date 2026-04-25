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

<div class="min-h-screen bg-base-100 flex flex-col font-sans selection:bg-primary/30">
    <!-- Header Premium -->
    <header class="sticky top-0 z-50 bg-base-100/80 backdrop-blur-xl border-b border-base-200">
        <div class="max-w-7xl mx-auto px-4 h-20 flex items-center justify-between font-outfit">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 bg-primary rounded-xl flex items-center justify-center text-primary-content shadow-lg shadow-primary/20">
                    <span class="text-xl font-black">B</span>
                </div>
                <div class="flex flex-col leading-none">
                    <span class="text-2xl font-black tracking-tighter text-base-content">
                        Black<span class="text-primary">Shot</span>
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

    <!-- Footer -->
    <footer class="footer footer-center p-10 bg-base-200 text-base-content rounded mt-20">
        <div>
            <div class="w-12 h-12 bg-primary/10 rounded-2xl flex items-center justify-center text-primary mb-2">
                <span class="text-xl font-black">B</span>
            </div>
            <p class="font-bold text-lg">
                Black<span class="text-primary">Shot</span> POS
            </p> 
            <p class="opacity-50 text-sm">Disfruta de nuestra selección premium.</p>
        </div> 
        <div>
            <div class="grid grid-flow-col gap-4">
                <p class="text-xs opacity-30">© 2024 - Todos los derechos reservados</p>
            </div>
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
