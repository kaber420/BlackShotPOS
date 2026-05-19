<script lang="ts">
	import '../app.css';
	let { children } = $props();
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
