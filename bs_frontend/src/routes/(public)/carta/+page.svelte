<script lang="ts">
    import { onMount } from 'svelte';
    import { ProductService } from '$lib/api/products';
    import type { Product } from '$lib/api/products';
    import { CategoryService } from '$lib/api/categories';
    import type { Category } from '$lib/api/categories';
    import { fade, fly } from 'svelte/transition';

    let products = $state<Product[]>([]);
    let categories = $state<Category[]>([]);
    let isLoading = $state(true);
    let selectedCategory = $state<number | null>(null);
    let errorMessage = $state('');

    const filteredProducts = $derived(
        selectedCategory 
            ? products.filter(p => p.category_id === selectedCategory && p.is_active)
            : products.filter(p => p.is_active)
    );

    async function loadData() {
        isLoading = true;
        errorMessage = '';
        try {
            const [fetchedProducts, fetchedCategories] = await Promise.all([
                ProductService.getAll(),
                CategoryService.getAll()
            ]);
            products = fetchedProducts;
            categories = fetchedCategories.filter(c => !c.is_modifier_category);
            
            // Default to first category if available
            if (categories.length > 0) {
                selectedCategory = categories[0].id || null;
            }
        } catch (error) {
            console.error('Error loading menu data:', error);
            errorMessage = 'Lo sentimos, no pudimos cargar el menú en este momento.';
        } finally {
            isLoading = false;
        }
    }

    onMount(loadData);
</script>

<svelte:head>
    <title>Nuestra Carta | BlackShot</title>
</svelte:head>

<div class="max-w-7xl mx-auto px-4 py-8 md:py-12">
    <!-- Hero Section -->
    <section class="text-center mb-12" in:fade={{ duration: 800 }}>
        <h1 class="text-4xl md:text-6xl font-black tracking-tight mb-4">
            Nuestra <span class="text-primary italic">Carta</span>
        </h1>
        <p class="text-lg opacity-60 max-w-2xl mx-auto">
            Descubre nuestra selección artesanal de platillos y bebidas preparados con los mejores ingredientes.
        </p>
    </section>

    <!-- Category Tabs -->
    <div class="sticky top-20 z-40 bg-base-100/95 backdrop-blur-md py-4 mb-8 -mx-4 px-4 overflow-x-auto no-scrollbar">
        <div class="flex gap-2 justify-start md:justify-center min-w-max">
            <button 
                class="btn btn-sm md:btn-md rounded-full px-6 transition-all {selectedCategory === null ? 'btn-primary' : 'btn-ghost'}"
                onclick={() => selectedCategory = null}
            >
                Todos
            </button>
            {#each categories as category}
                <button 
                    class="btn btn-sm md:btn-md rounded-full px-6 transition-all {selectedCategory === category.id ? 'btn-primary' : 'btn-ghost bg-base-200/50'}"
                    onclick={() => selectedCategory = category.id || null}
                >
                    {category.name}
                </button>
            {/each}
        </div>
    </div>

    {#if errorMessage}
        <div class="max-w-md mx-auto text-center py-20">
            <div class="alert alert-error shadow-inner rounded-2xl mb-4">
                <span>{errorMessage}</span>
            </div>
            <button class="btn btn-primary" onclick={loadData}>Reintentar</button>
        </div>
    {/if}

    <!-- Products Grid -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {#if isLoading}
            {#each Array(8) as _}
                <div class="flex flex-col gap-4 animate-pulse">
                    <div class="bg-base-300 rounded-3xl aspect-[4/3] w-full"></div>
                    <div class="h-6 bg-base-300 rounded-lg w-3/4"></div>
                    <div class="h-4 bg-base-300 rounded-lg w-full"></div>
                    <div class="h-8 bg-base-300 rounded-lg w-1/3 mt-2"></div>
                </div>
            {/each}
        {:else}
            {#each filteredProducts as product (product.id)}
                <div 
                    class="group relative bg-base-100 border border-base-200 rounded-[2rem] overflow-hidden hover:shadow-2xl hover:shadow-primary/5 transition-all duration-500 hover:-translate-y-1"
                    in:fly={{ y: 20, duration: 400 }}
                >
                    <!-- Image Area -->
                    <div class="aspect-[4/3] w-full relative overflow-hidden bg-base-200">
                        {#if product.image_url}
                            <img 
                                src={product.image_url} 
                                alt={product.name} 
                                class="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
                            />
                        {:else}
                            <div class="w-full h-full flex items-center justify-center bg-gradient-to-br from-primary/5 to-primary/10">
                                <span class="text-5xl font-black text-primary/20 opacity-30 select-none">
                                    {product.name.charAt(0).toUpperCase()}
                                </span>
                            </div>
                        {/if}
                        
                        <!-- Badges Overlay -->
                        <div class="absolute top-4 left-4 flex gap-2">
                            {#if product.calories}
                                <span class="badge badge-sm bg-black/50 backdrop-blur-md text-white border-0 font-bold px-3">
                                    {product.calories} kcal
                                </span>
                            {/if}
                        </div>
                    </div>

                    <!-- Info Area -->
                    <div class="p-6">
                        <div class="flex justify-between items-start gap-2 mb-2">
                            <h3 class="text-xl font-bold leading-tight group-hover:text-primary transition-colors">
                                {product.name}
                            </h3>
                            <span class="text-2xl font-black text-base-content/90 font-mono tracking-tighter">
                                ${product.price.toFixed(0)}
                            </span>
                        </div>
                        
                        {#if product.description}
                            <p class="text-sm opacity-50 line-clamp-2 mb-4">
                                {product.description}
                            </p>
                        {/if}

                        <!-- Nutritional Info (Simplified) -->
                        {#if product.protein || product.carbs || product.fats}
                            <div class="flex gap-4 pt-4 border-t border-base-200 text-[10px] font-bold uppercase tracking-widest opacity-40">
                                {#if product.protein}
                                    <div class="flex flex-col">
                                        <span>Proteína</span>
                                        <span class="text-base-content">{product.protein}g</span>
                                    </div>
                                {/if}
                                {#if product.carbs}
                                    <div class="flex flex-col">
                                        <span>Carbos</span>
                                        <span class="text-base-content">{product.carbs}g</span>
                                    </div>
                                {/if}
                                {#if product.fats}
                                    <div class="flex flex-col">
                                        <span>Grasas</span>
                                        <span class="text-base-content">{product.fats}g</span>
                                    </div>
                                {/if}
                            </div>
                        {/if}
                    </div>
                </div>
            {/each}
        {/if}
    </div>

    {#if !isLoading && filteredProducts.length === 0}
        <div class="text-center py-20 opacity-30 italic">
            No hay productos disponibles en esta categoría por el momento.
        </div>
    {/if}
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
