<script lang="ts">
	import { onMount } from 'svelte';
	import { fade, scale } from 'svelte/transition';
	import { fetchApi } from '$lib/api';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
	import { ProductService, type Product } from '$lib/api/products';
	import { CategoryService, type Category } from '$lib/api/categories';
	import { OrderService, OrderStatus } from '$lib/api/orders';
	import { appState, addToCart, loadOrderToCart } from '$lib/app_state.svelte';
	import ProductCustomizer from '$lib/components/ProductCustomizer.svelte';
	import { addToast } from '$lib/toast.svelte.js';
    import Button from '$lib/components/ui/Button.svelte';
	import { posSocket } from '$lib/pos_socket.svelte';

	let categories = $state<Category[]>([]);
	let products = $state<Product[]>([]);
	let selectedCategory = $state<number | null>(null);
	let isLoading = $state(true);

	// Operational Stats derived from global socket
	let preparingCount = $derived(posSocket.dashboardStats?.preparingCount ?? 0);
	let readyCount = $derived(posSocket.dashboardStats?.readyCount ?? 0);
	let starProductToday = $derived(posSocket.dashboardStats?.starProductToday ?? "Ninguno aún");
	let starProductWeek = $derived(posSocket.dashboardStats?.starProductWeek ?? "Ninguno aún");
	let showWeeklyStar = $state(false);

	// Modal State
	let showCustomizer = $state(false);
	let activeProduct = $state<any>(null);
	let infoProductId = $state<number | null>(null);

	onMount(async () => {
		// Subscribe to real-time stats
		posSocket.subscribe("dashboard_stats");

		try {
			categories = await CategoryService.getAll();
			if (categories.length > 0) {
				selectedCategory = categories[0].id || null;
				await loadProducts(selectedCategory);
			}

            // Detección de orden vía URL (Cobro desde lista de órdenes)
            const orderId = page.url.searchParams.get('order_id');
            if (orderId) {
                const order = await OrderService.getById(parseInt(orderId));
                loadOrderToCart(order);
            }

		} catch (e) {
			console.error("Error loading initial data", e);
		} finally {
			isLoading = false;
		}

		return () => {
			posSocket.unsubscribe("dashboard_stats");
		};
	});

    // Rotation for Star Product
    $effect(() => {
        const interval = setInterval(() => {
            showWeeklyStar = !showWeeklyStar;
        }, 8000);
        return () => clearInterval(interval);
    });




	async function loadProducts(categoryId: number | null) {
		isLoading = true;
		selectedCategory = categoryId;
		try {
			products = await ProductService.getAll(categoryId || undefined);
		} catch (e) {
			console.error("Error loading products", e);
		} finally {
			isLoading = false;
		}
	}

	function handleProductClick(product: any) {
		activeProduct = product;
		// Mostrar modal si tiene modificadores O variantes (tallas)
		const hasModifiers = product.modifier_groups && product.modifier_groups.length > 0;
		const hasVariants = product.variants && product.variants.length > 0;
		
		if (hasModifiers || hasVariants) {
			showCustomizer = true;
		} else {
			addToCart(product);
		}
	}

	function onConfirmCustomization(modifiers: any[], variant?: any) {
		addToCart(activeProduct, modifiers, variant);
		showCustomizer = false;
		activeProduct = null;
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
            return words.map((w: string) => w[0]).join('').toUpperCase().substring(0, 2);
        }
        return name.substring(0, 2).toUpperCase();
    }

</script>

<div class="p-4 md:p-6 lg:p-8 flex flex-col gap-6 h-full">

	<!-- Main POS View Layout -->
	<div class="flex flex-col lg:flex-row gap-6 flex-1 min-h-0">
		
		<!-- Left: Categories & Products (100%) -->
		<div class="w-full flex flex-col gap-4 h-full min-h-0">
			<!-- Categories & Compact Stats Row -->
			<div class="flex items-center justify-between bg-base-100 shadow-sm p-2 rounded-xl border border-base-200">
                <!-- Categories Tabs -->
                <div class="flex gap-2 overflow-x-auto whitespace-nowrap elegant-scroll no-scrollbar flex-1 pr-4">
                    {#each categories as cat}
                        <Button 
                            variant={selectedCategory === (cat.id ?? null) ? 'primary' : 'ghost'}
                            size="sm"
                            class="rounded-lg transition-all"
                            onclick={() => loadProducts(cat.id ?? null)}
                        >
                            {cat.name}
                        </Button>
                    {/each}
                </div>

                <!-- Compact Live Status -->
                <div class="flex items-center gap-2 pl-4 border-l border-base-200">
                    <div class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-warning/10 text-warning border border-warning/20" title="Órdenes en cocina">
                        <span class="text-xs font-black">🍳</span>
                        <span class="text-sm font-black font-mono">{preparingCount}</span>
                    </div>
                    <div class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-success/10 text-success border border-success/20" title="Listos para entrega">
                        <span class="text-xs font-black">✅</span>
                        <span class="text-sm font-black font-mono">{readyCount}</span>
                    </div>
                </div>
			</div>
			
			<!-- Product Grid -->
			<div class="flex-1 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3.5 overflow-y-auto pb-4 pr-2 min-h-0">
				{#if isLoading}
					<div class="col-span-full flex justify-center py-20">
						<span class="loading loading-spinner loading-lg text-primary"></span>
					</div>
				{:else}
					{#each products as prod}
                        {@const hasModifiers = prod.modifier_groups && prod.modifier_groups.length > 0}
                        {@const hasVariants = prod.variants && prod.variants.length > 0}
                        {@const hasOptions = hasModifiers || hasVariants}
						<div class="relative group aspect-square">
							<button 
								class="card w-full h-full bg-base-100 border border-base-200 rounded-[2rem] overflow-hidden transition-all duration-500 text-left {prod.is_active ? 'hover:shadow-2xl hover:shadow-primary/20 hover:-translate-y-1 cursor-pointer active:scale-[0.98]' : 'opacity-70 grayscale-[0.5] cursor-not-allowed'}"
								onclick={() => prod.is_active && handleProductClick(prod)}
							>
								<div class="relative w-full h-full">
                                    <!-- Product Image -->
									{#if prod.image_url}
										<img src={prod.image_url} alt={prod.name} class="w-full h-full object-cover transition-transform duration-700 {prod.is_active ? 'group-hover:scale-110' : ''}" />
									{:else}
										<div class="w-full h-full flex items-center justify-center bg-gradient-to-br from-primary/20 to-primary/40">
											<span class="text-5xl font-black text-white/40 select-none">
												{prod.name.charAt(0).toUpperCase()}
											</span>
										</div>
									{/if}

                                    <!-- Gradient Overlay -->
                                    <div class="absolute inset-0 bg-gradient-to-t from-black/90 via-black/20 to-transparent opacity-80 group-hover:opacity-100 transition-opacity"></div>

                                    <!-- Top Seller Badges -->
                                    <div class="absolute top-3 left-3 z-20 flex flex-col gap-1.5 items-start">
                                        {#if prod.name === starProductToday}
                                            <span class="bg-orange-600/90 text-white text-[10px] font-black px-2.5 py-1 rounded-lg shadow-lg backdrop-blur-md uppercase tracking-tighter border border-white/10">🔥 TOP HOY</span>
                                        {/if}
                                        {#if prod.name === starProductWeek}
                                            <span class="bg-amber-600/90 text-white text-[10px] font-black px-2.5 py-1 rounded-lg shadow-lg backdrop-blur-md uppercase tracking-tighter border border-white/10">⭐ TOP SEMANA</span>
                                        {/if}
                                    </div>

                                    <!-- Intelligent Quick Add (Top Right) -->
                                    {#if prod.is_active}
                                        {#if !hasOptions}
                                            <button 
                                                class="absolute top-3 right-3 z-30 w-10 h-10 bg-white/20 hover:bg-primary backdrop-blur-md border border-white/30 text-white rounded-full flex items-center justify-center shadow-xl transition-all duration-300 transform scale-0 group-hover:scale-100 active:scale-90"
                                                onclick={(e) => { e.stopPropagation(); addToCart(prod); addToast(`Añadido: ${prod.name}`, 'success'); }}
                                                title="Añadir rápido"
                                            >
                                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="3" stroke="currentColor" class="w-5 h-5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
                                            </button>
                                        {:else}
                                            <div class="absolute top-3 right-3 z-30 w-10 h-10 bg-black/20 backdrop-blur-md border border-white/10 text-white/70 rounded-full flex items-center justify-center transform scale-0 group-hover:scale-100 transition-transform duration-300" title="Requiere configuración">
                                                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-5 h-5"><path stroke-linecap="round" stroke-linejoin="round" d="M10.5 6h9.75M10.5 6a1.5 1.5 0 11-3 0m3 0a1.5 1.5 0 10-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 11-3 0m3 0a1.5 1.5 0 10-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 11-3 0m3 0a1.5 1.5 0 10-3 0m-9.75 0h9.75" /></svg>
                                            </div>
                                        {/if}
                                    {/if}

                                    {#if !prod.is_active}
                                        <div class="absolute inset-0 bg-black/40 backdrop-blur-[2px] flex items-center justify-center p-2">
                                            <div class="bg-white/90 text-black px-3 py-1 rounded-xl shadow-md font-black uppercase tracking-tighter text-xs">
                                                No Disponible
                                            </div>
                                        </div>
                                    {/if}

                                    <!-- Product Info (Overlay Bottom) -->
                                    <div class="absolute bottom-0 left-0 w-full p-4 flex flex-col gap-1">
                                        <h3 class="text-white font-black text-sm leading-tight drop-shadow-lg line-clamp-2">{prod.name}</h3>
                                        
                                        <div class="flex items-center justify-between mt-1">
                                            <!-- Price Area -->
                                            <div class="flex flex-wrap gap-1.5">
                                                {#if hasVariants}
                                                    {#each prod.variants.slice(0, 3) as variant}
                                                        <div class="bg-white/10 backdrop-blur-md border border-white/20 rounded-lg px-2 py-1 flex items-center gap-1.5 shadow-sm">
                                                            <span class="text-[8px] font-black text-white/50 uppercase tracking-tighter">
                                                                {getInitials(variant.measure?.name)}
                                                            </span>
                                                            <span class="text-[10px] font-black text-white">
                                                                ${variant.price.toFixed(0)}
                                                            </span>
                                                        </div>
                                                    {/each}
                                                {:else}
                                                    <div class="bg-white/10 backdrop-blur-md border border-white/20 rounded-full px-3 py-1 text-white font-black text-xs shadow-inner">
                                                        ${prod.price?.toFixed(0) ?? '0'}
                                                    </div>
                                                {/if}
                                            </div>

                                            {#if prod.description}
                                                <button 
                                                    class="text-white/40 hover:text-white transition-colors"
                                                    onclick={(e) => { e.stopPropagation(); infoProductId = prod.id; }}
                                                    title="Ver descripción"
                                                >
                                                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-4 h-4"><path stroke-linecap="round" stroke-linejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" /></svg>
                                                </button>
                                            {/if}
                                        </div>
                                    </div>
								</div>
							</button>

							{#if infoProductId === prod.id}
								<div 
									class="absolute inset-0 z-40 bg-black/60 backdrop-blur-md rounded-[2rem] p-4 flex flex-col items-center justify-center text-center shadow-2xl pointer-events-auto"
									onclick={(e) => { e.stopPropagation(); infoProductId = null; }}
                                    aria-hidden="true"
									transition:fade={{ duration: 150 }}
								>
									<div 
										class="flex flex-col items-center justify-center h-full w-full"
										in:scale={{ duration: 200, start: 0.95 }}
									>
										<div class="absolute top-4 right-4">
											<Button variant="ghost" circle size="xs" class="text-white/40 hover:text-white">
												<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="3" stroke="currentColor" class="w-4 h-4"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
											</Button>
										</div>
										<h4 class="font-black text-xs uppercase tracking-widest text-primary mb-3">{prod.name}</h4>
										<div class="flex-1 overflow-y-auto w-full px-2 elegant-scroll">
											<p class="text-[11px] leading-relaxed text-white/90 text-left">
												{prod.description}
											</p>
										</div>
										<div class="mt-4 text-[9px] font-bold uppercase tracking-tighter text-white/20 animate-pulse">Tocar para cerrar</div>
									</div>
								</div>
							{/if}
						</div>
					{/each}
				{/if}
			</div>
		</div>

	</div>
</div>

<ProductCustomizer 
	product={activeProduct} 
	isOpen={showCustomizer} 
	onClose={() => { showCustomizer = false; activeProduct = null; }}
	onConfirm={onConfirmCustomization}
/>


<style>
	.tabs-box::-webkit-scrollbar,
    .no-scrollbar::-webkit-scrollbar {
		display: none;
	}

	.custom-scrollbar::-webkit-scrollbar {
		width: 3px;
	}
	.custom-scrollbar::-webkit-scrollbar-thumb {
		background: rgba(var(--p), 0.2);
		border-radius: 10px;
	}
</style>
