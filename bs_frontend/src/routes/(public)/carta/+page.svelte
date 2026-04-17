<script lang="ts">
    import { onMount } from 'svelte';
    import { ProductService } from '$lib/api/products';
    import type { Product } from '$lib/api/products';
    import { CategoryService } from '$lib/api/categories';
    import type { Category } from '$lib/api/categories';
    import { fade, fly } from 'svelte/transition';
    import Button from '$lib/components/ui/Button.svelte';

    let products = $state<Product[]>([]);
    let categories = $state<Category[]>([]);
    let isLoading = $state(true);
    let selectedCategory = $state<number | null>(null);
    let errorMessage = $state('');

    const filteredProducts = $derived(
        selectedCategory 
            ? products.filter(p => p.category_id === selectedCategory)
            : products
    );

    async function loadData() {
        isLoading = true;
        errorMessage = '';
        try {
            const [fetchedProducts, fetchedCategories] = await Promise.all([
                ProductService.getAll(undefined, true),
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

    function getDisplayPrice(product: Product) {
        // 1. Si hay variantes con precios válidos, priorizamos eso
        if (product.variants && product.variants.length > 0) {
            const prices = product.variants
                .map(v => v.price)
                .filter(p => p > 0);
            
            if (prices.length > 0) {
                const minPrice = Math.min(...prices);
                const maxPrice = Math.max(...prices);
                if (minPrice === maxPrice) return `$${minPrice.toFixed(0)}`;
                return `Desde $${minPrice.toFixed(0)}`;
            }
        }
        
        // 2. Si no hay variantes, usamos el precio base si es >= 1
        if (product.price && product.price >= 1) {
            return `$${product.price.toFixed(0)}`;
        }
        
        // 3. Caso especial: si es 0, no mostramos precio
        return null;
    }

    function getInitials(name: string | undefined) {
        if (!name) return '';
        if (name.length <= 2) return name.toUpperCase();
        
        const lower = name.toLowerCase();
        if (lower.startsWith('chi')) return 'CH';
        if (lower.startsWith('med')) return 'ME';
        if (lower.startsWith('gra')) return 'GR';
        if (lower.startsWith('ext')) return 'EX';
        
        // Fallback: first 2 letters or first letter of each word
        const words = name.split(' ');
        if (words.length > 1) {
            return words.map(w => w[0]).join('').toUpperCase().substring(0, 2);
        }
        return name.substring(0, 2).toUpperCase();
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
            <Button 
                variant={selectedCategory === null ? 'primary' : 'outline'}
                size="sm"
                class="rounded-full px-6 transition-all {selectedCategory === null ? 'shadow-lg shadow-primary/20' : 'border-base-300'}"
                onclick={() => selectedCategory = null}
            >
                Todos
            </Button>
            {#each categories as category}
                <Button 
                    variant={selectedCategory === category.id ? 'primary' : 'outline'}
                    size="sm"
                    class="rounded-full px-6 transition-all {selectedCategory === category.id ? 'shadow-lg shadow-primary/20' : 'border-base-300 bg-base-200/5'}"
                    onclick={() => selectedCategory = category.id || null}
                >
                    {category.name}
                </Button>
            {/each}
        </div>
    </div>

    {#if errorMessage}
        <div class="max-w-md mx-auto text-center py-20">
            <div class="alert alert-error shadow-inner rounded-2xl mb-4">
                <span>{errorMessage}</span>
            </div>
            <Button variant="primary" onclick={loadData}>Reintentar</Button>
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
                    class="group relative bg-base-100 border border-base-200 rounded-[2rem] overflow-hidden transition-all duration-500 {product.is_active ? 'hover:shadow-2xl hover:shadow-primary/5 hover:-translate-y-1' : 'opacity-70 grayscale-[0.5]'}"
                    in:fly={{ y: 20, duration: 400 }}
                >
                    <!-- Image Area -->
                    <div class="aspect-[4/3] w-full relative overflow-hidden bg-base-200">
                        {#if product.image_url}
                            <img 
                                src={product.image_url} 
                                alt={product.name} 
                                class="w-full h-full object-cover transition-transform duration-700 {product.is_active ? 'group-hover:scale-110' : ''}"
                            />
                        {:else}
                            <div class="w-full h-full flex items-center justify-center bg-gradient-to-br from-primary/5 to-primary/10">
                                <span class="text-5xl font-black text-primary/20 opacity-30 select-none">
                                    {product.name.charAt(0).toUpperCase()}
                                </span>
                            </div>
                        {/if}
                        
                        {#if !product.is_active}
                            <div class="absolute inset-0 bg-base-300/60 backdrop-blur-[2px] flex items-center justify-center p-6">
                                <div class="bg-base-100/90 text-base-content px-6 py-3 rounded-2xl shadow-xl border border-base-300 transform -rotate-3 font-black uppercase tracking-tighter text-sm">
                                    No Disponible
                                </div>
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
                        <div class="flex flex-col gap-1 mb-2">
                            <h3 class="text-xl font-bold leading-tight group-hover:text-primary transition-colors">
                                {product.name}
                            </h3>
                            
                            <div class="flex flex-wrap items-center gap-2 mt-1">
                                {#if product.variants && product.variants.length > 0}
                                    {#each product.variants as variant}
                                        {#if variant.price > 0}
                                            <div class="flex items-center gap-1.5 bg-base-200/50 px-2 py-1 rounded-lg border border-base-300/30">
                                                <span class="text-[9px] font-black opacity-40 uppercase tracking-tighter">
                                                    {getInitials(variant.measure?.name)}
                                                </span>
                                                <span class="font-mono font-bold text-sm">
                                                    ${variant.price.toFixed(0)}
                                                </span>
                                            </div>
                                        {/if}
                                    {/each}
                                {:else if product.price && product.price >= 1}
                                    <span class="text-2xl font-black text-base-content/90 font-mono tracking-tighter">
                                        ${product.price.toFixed(0)}
                                    </span>
                                {/if}
                            </div>
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
