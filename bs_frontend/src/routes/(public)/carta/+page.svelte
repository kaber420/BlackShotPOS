<script lang="ts">
    import { onMount } from 'svelte';
    import { ProductService } from '$lib/api/products';
    import type { Product } from '$lib/api/products';
    import { CategoryService } from '$lib/api/categories';
    import type { Category } from '$lib/api/categories';
    import { SettingsService } from '$lib/api/settings';
    import type { BusinessSettings } from '$lib/api/settings';
    import { fade, fly, slide } from 'svelte/transition';
    import { quintOut } from 'svelte/easing';
    import Button from '$lib/components/ui/Button.svelte';
    import ProductMedia from '$lib/components/ProductMedia.svelte';

    let products = $state<Product[]>([]);
    let categories = $state<Category[]>([]);
    let settings = $state<BusinessSettings | null>(null);
    let isLoading = $state(true);
    let selectedCategory = $state<number | null>(null);
    let searchTerm = $state('');
    let errorMessage = $state('');

    // Menu logic: Filters if selectedCategory is set, otherwise shows everything grouped
    const menuSections = $derived(
        categories.map(cat => {
            const catProducts = products.filter(p => 
                p.category_id === cat.id && 
                (searchTerm === '' || p.name.toLowerCase().includes(searchTerm.toLowerCase()))
            );
            return { ...cat, products: catProducts };
        }).filter(section => {
            if (selectedCategory !== null) return section.id === selectedCategory && section.products.length > 0;
            return section.products.length > 0;
        })
    );

    async function loadData() {
        isLoading = true;
        errorMessage = '';
        try {
            const [fetchedProducts, fetchedCategories, fetchedSettings] = await Promise.all([
                ProductService.getAll(undefined, true),
                CategoryService.getAll(),
                SettingsService.get()
            ]);
            products = fetchedProducts;
            categories = fetchedCategories.filter(c => !c.is_modifier_category);
            settings = fetchedSettings;
        } catch (error) {
            console.error('Error loading menu data:', error);
            errorMessage = 'Error al cargar la carta.';
        } finally {
            isLoading = false;
        }
    }

    function getInitials(name: string | undefined) {
        if (!name) return '';
        const words = name.split(' ');
        return words.map(w => w[0]).join('').toUpperCase().substring(0, 2);
    }

    onMount(loadData);
</script>

<svelte:head>
    <title>{settings?.menu_title || 'Carta'} | BlackShot</title>
</svelte:head>

<div class="min-h-screen bg-base-100 pb-20">
    <!-- Header Minimalista y Premium -->
    <header class="pt-10 pb-6 px-4 max-w-7xl mx-auto flex flex-col items-center text-center">
        <h1 class="text-4xl md:text-5xl font-black tracking-tighter uppercase mb-2 bg-gradient-to-b from-base-content to-base-content/60 bg-clip-text text-transparent">
            {settings?.menu_title || 'Nuestra Selección'}
        </h1>
        {#if settings?.menu_subtitle}
            <p class="text-xs uppercase tracking-[0.3em] font-bold opacity-30">
                {settings.menu_subtitle}
            </p>
        {/if}
    </header>

    <!-- Navigation & Filters -->
    <div class="sticky top-[80px] z-40 bg-base-100/80 backdrop-blur-xl border-y border-base-200 py-4 mb-10 shadow-sm">
        <div class="max-w-7xl mx-auto px-4 flex flex-col md:flex-row items-center justify-between gap-4">
            <div class="flex gap-2 overflow-x-auto no-scrollbar w-full md:w-auto pb-2 md:pb-0">
                <button 
                    class="h-10 px-6 rounded-2xl text-[11px] font-black uppercase tracking-widest transition-all whitespace-nowrap 
                    {selectedCategory === null ? 'bg-primary text-primary-content shadow-xl shadow-primary/20' : 'bg-base-200 text-base-content/60 hover:bg-base-300'}"
                    onclick={() => selectedCategory = null}
                >
                    Todos
                </button>
                {#each categories as category}
                    <button 
                        class="h-10 px-6 rounded-2xl text-[11px] font-black uppercase tracking-widest transition-all whitespace-nowrap 
                        {selectedCategory === category.id ? 'bg-primary text-primary-content shadow-xl shadow-primary/20' : 'bg-base-200 text-base-content/60 hover:bg-base-300'}"
                        onclick={() => selectedCategory = category.id || null}
                    >
                        {category.name}
                    </button>
                {/each}
            </div>

            <!-- Search -->
            <div class="relative w-full md:w-64">
                <input 
                    type="text" 
                    placeholder="¿Qué se te antoja?" 
                    bind:value={searchTerm}
                    class="input input-bordered w-full rounded-2xl bg-base-200/50 border-none focus:ring-2 focus:ring-primary/20 transition-all font-bold text-sm"
                />
            </div>
        </div>
    </div>

    <!-- Menu Content -->
    <main class="max-w-7xl mx-auto px-4">
        {#if isLoading}
            <div class="grid grid-cols-2 lg:grid-cols-4 gap-6">
                {#each Array(8) as _}
                    <div class="aspect-[4/5] bg-base-200 rounded-[2.5rem] animate-pulse"></div>
                {/each}
            </div>
        {:else if errorMessage}
            <div class="text-center py-20">
                <p class="text-error font-bold">{errorMessage}</p>
                <button class="btn btn-primary mt-4" onclick={loadData}>Reintentar</button>
            </div>
        {:else}
            <div class="flex flex-col gap-20">
                {#each menuSections as section (section.id)}
                    <section in:fade={{ duration: 300 }}>
                        {#if selectedCategory === null}
                            <div class="flex items-center gap-6 mb-10">
                                <h2 class="text-3xl font-black uppercase tracking-tighter">{section.name}</h2>
                                <div class="h-1 flex-1 bg-base-200 rounded-full"></div>
                            </div>
                        {/if}

                        <div class="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 md:gap-8">
                            {#each section.products as product (product.id)}
                                <div 
                                    class="group relative aspect-[4/5] bg-base-200 rounded-[3rem] overflow-hidden border border-base-200 transition-all duration-500 {product.is_active ? 'hover:shadow-[0_30px_60px_-15px_rgba(0,0,0,0.3)] hover:-translate-y-3' : 'opacity-40 grayscale'}"
                                    in:fly={{ y: 20, duration: 400, delay: 100 }}
                                >
                                    <!-- Image -->
                                    <div class="absolute inset-0">
                                        {#if product.image_url}
                                            <ProductMedia src={product.image_url} alt={product.name} />
                                        {:else}
                                            <div class="w-full h-full flex items-center justify-center bg-gradient-to-br from-base-300 to-base-200">
                                                <span class="text-7xl font-black opacity-5 select-none">{product.name.charAt(0)}</span>
                                            </div>
                                        {/if}
                                    </div>

                                    <!-- Floating Glass Card -->
                                    <div class="absolute inset-x-3 bottom-3 md:inset-x-5 md:bottom-5 p-5 bg-black/20 backdrop-blur-3xl border border-white/10 rounded-[2rem] text-white shadow-2xl transition-all duration-500 group-hover:bg-black/40">
                                        <h3 class="text-sm md:text-lg font-black uppercase tracking-tight mb-2 truncate">
                                            {product.name}
                                        </h3>
                                        
                                        <div class="flex items-center justify-between">
                                            <div class="flex gap-2">
                                                {#if product.variants && product.variants.length > 0}
                                                    {#each product.variants.slice(0, 3) as variant}
                                                        <div class="flex flex-col items-center">
                                                            <span class="text-[7px] font-black opacity-50 mb-0.5 uppercase">{getInitials(variant.measure?.name)}</span>
                                                            <span class="text-[10px] md:text-xs font-mono font-black bg-white/10 px-2 py-1 rounded-lg border border-white/5">
                                                                ${variant.price.toFixed(0)}
                                                            </span>
                                                        </div>
                                                    {/each}
                                                {:else}
                                                    <span class="text-xl font-black font-mono tracking-tighter">
                                                        ${product.price.toFixed(0)}
                                                    </span>
                                                {/if}
                                            </div>
                                            
                                            {#if product.calories}
                                                <div class="text-[9px] font-black opacity-40 px-2 py-1 rounded-full border border-white/10 uppercase">
                                                    {product.calories} kcal
                                                </div>
                                            {/if}
                                        </div>
                                    </div>

                                    {#if !product.is_active}
                                        <div class="absolute inset-0 bg-base-300/60 backdrop-blur-sm flex items-center justify-center">
                                            <span class="bg-black text-white text-[10px] font-black uppercase px-5 py-2 rounded-2xl">Agotado</span>
                                        </div>
                                    {/if}
                                </div>
                            {/each}
                        </div>
                    </section>
                {/each}
            </div>

            {#if menuSections.length === 0}
                <div class="text-center py-40 opacity-20 italic font-bold text-2xl">
                    No encontramos nada con ese nombre...
                </div>
            {/if}
        {/if}
    </main>
</div>

<style>
    .no-scrollbar::-webkit-scrollbar {
        display: none;
    }
    .no-scrollbar {
        -ms-overflow-style: none;
        scrollbar-width: none;
    }
</style>
