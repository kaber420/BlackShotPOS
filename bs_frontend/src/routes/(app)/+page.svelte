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

	let categories = $state<Category[]>([]);
	let products = $state<Product[]>([]);
	let selectedCategory = $state<number | null>(null);
	let isLoading = $state(true);

	// Operational Stats State
	let preparingCount = $state(0);
	let readyCount = $state(0);
	let starProductToday = $state("Cargando...");
	let starProductWeek = $state("Cargando...");
	let showWeeklyStar = $state(false);
	let ws: WebSocket | null = null;

	// Modal State
	let showCustomizer = $state(false);
	let activeProduct = $state<any>(null);
	let infoProductId = $state<number | null>(null);

	onMount(async () => {
		try {
			categories = await CategoryService.getAll();
			if (categories.length > 0) {
				selectedCategory = categories[0].id || null;
				await loadProducts(selectedCategory);
			}

            // Si hay una orden activa (desde el tablero de mesas), cargar sus items al carrito
            // (Para simplicidad en este MVP, las órdenes se completan en una sesión)
            
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
	});

    // Rotation for Star Product
    $effect(() => {
        const interval = setInterval(() => {
            showWeeklyStar = !showWeeklyStar;
        }, 8000);
        return () => clearInterval(interval);
    });

    // Real-time stats via WebSocket
    $effect(() => {
        let socket: WebSocket | null = null;
        let reconnectTimeout: any;

        function connect() {
            const token = localStorage.getItem('X-Omni-Token') || '';
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = window.location.host;
            const url = `${protocol}//${host}/api/v1/pos/ws/pos?token=${encodeURIComponent(token)}`;

            socket = new WebSocket(url);
            ws = socket; // Export for other functions if needed

            socket.onopen = () => {
                console.log("🔌 Dashboard WS conectado");
                socket?.send(JSON.stringify({ action: "subscribe", topic: "dashboard_stats" }));
            };

            socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.preparingCount !== undefined) {
                        preparingCount = data.preparingCount;
                        readyCount = data.readyCount;
                        starProductToday = data.starProductToday;
                        starProductWeek = data.starProductWeek;
                    }
                } catch (e) {
                    console.error("Error parsing WS data", e);
                }
            };

            socket.onclose = () => {
                console.log("🔌 Dashboard WS desconectado. Reconectando en 5s...");
                reconnectTimeout = setTimeout(connect, 5000);
            };
        }

        connect();

        return () => {
            socket?.close();
            clearTimeout(reconnectTimeout);
        };
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
	<!-- Top Operational Row -->
	<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
		<div class="stat bg-base-100 rounded-box shadow-sm border border-base-200">
			<div class="stat-title uppercase text-[10px] font-black tracking-widest opacity-60">En Cocina</div>
			<div class="stat-value text-warning font-serif">{preparingCount}</div>
			<div class="stat-desc">Órdenes pendientes</div>
		</div>
		<div class="stat bg-base-100 rounded-box shadow-sm border border-base-200">
			<div class="stat-title uppercase text-[10px] font-black tracking-widest opacity-60">Listos</div>
			<div class="stat-value text-success">{readyCount}</div>
			<div class="stat-desc">Para entregar</div>
		</div>
		<div class="stat bg-base-100 rounded-box shadow-sm border border-base-200 overflow-hidden">
			<div class="stat-title uppercase text-[10px] font-black tracking-widest opacity-60">
                ⭐ Producto Estrella ({showWeeklyStar ? 'Semana' : 'Hoy'})
            </div>
			<div class="stat-value text-accent text-2xl font-bold truncate">
                {showWeeklyStar ? starProductWeek : starProductToday}
            </div>
			<div class="stat-desc">Rotando cada 8 segundos</div>
		</div>
	</div>

	<!-- Main POS View Layout -->
	<div class="flex flex-col lg:flex-row gap-6 flex-1 min-h-0">
		
		<!-- Left: Categories & Products (100%) -->
		<div class="w-full flex flex-col gap-4 h-full min-h-0">
			<!-- Categories Tabs -->
			<div class="flex gap-2 bg-base-100 shadow-sm p-2 rounded-xl border border-base-200 overflow-x-auto whitespace-nowrap elegant-scroll">
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
			
			<!-- Product Grid -->
			<div class="flex-1 grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4 overflow-y-auto pb-4 pr-2 min-h-0">
				{#if isLoading}
					<div class="col-span-full flex justify-center py-20">
						<span class="loading loading-spinner loading-lg text-primary"></span>
					</div>
				{:else}
					{#each products as prod}
						<div class="relative group aspect-[3/4.5]">
							<button 
								class="card w-full h-full bg-base-100 border border-base-200 rounded-2xl overflow-hidden transition-all duration-500 text-left {prod.is_active ? 'hover:shadow-xl hover:shadow-primary/5 hover:-translate-y-0.5 cursor-pointer active:scale-[0.98]' : 'opacity-70 grayscale-[0.5] cursor-not-allowed'}"
								onclick={() => prod.is_active && handleProductClick(prod)}
							>
								<div class="flex flex-col h-full">
									<div class="aspect-square w-full relative overflow-hidden bg-base-200">
										{#if prod.image_url}
											<img src={prod.image_url} alt={prod.name} class="w-full h-full object-cover transition-transform duration-700 {prod.is_active ? 'group-hover:scale-110' : ''}" />
										{:else}
											<div class="w-full h-full flex items-center justify-center bg-gradient-to-br from-primary/5 to-primary/10">
												<span class="text-3xl font-black text-primary/20 opacity-30 select-none">
													{prod.name.charAt(0).toUpperCase()}
												</span>
											</div>
										{/if}

										{#if !prod.is_active}
											<div class="absolute inset-0 bg-base-300/60 backdrop-blur-[1px] flex items-center justify-center p-2">
												<div class="bg-base-100/90 text-base-content px-2 py-1 rounded-lg shadow-md border border-base-300 transform -rotate-2 font-black uppercase tracking-tighter text-[10px]">
													No Disponible
												</div>
											</div>
										{/if}
									</div>

									<div class="p-3 flex-1 flex flex-col justify-between">
										<h3 class="text-sm font-bold leading-tight group-hover:text-primary transition-colors line-clamp-2 mb-2">{prod.name}</h3>
										<div class="flex items-center justify-between mt-auto">
											<div class="flex flex-wrap items-center gap-1.5 min-h-[22px]">
												{#if prod.variants && prod.variants.length > 0}
													{#each prod.variants.slice(0, 2) as variant}
														{#if variant.price > 0}
															<div class="flex items-center gap-1 bg-base-200/50 px-1.5 py-0.5 rounded border border-base-300/30">
																<span class="text-[8px] font-black opacity-40 uppercase tracking-tighter">
																	{getInitials(variant.measure?.name)}
																</span>
																<span class="font-mono font-bold text-xs">
																	${variant.price.toFixed(0)}
																</span>
															</div>
														{/if}
													{/each}
													{#if prod.variants.length > 2}
														<span class="text-[8px] opacity-40">...</span>
													{/if}
												{:else if prod.price && prod.price >= 0}
													<span class="text-base font-black text-base-content/90 font-mono tracking-tighter">
														${prod.price.toFixed(0)}
													</span>
												{/if}
											</div>
											
											{#if prod.description}
												<Button 
                                                    variant="ghost"
                                                    circle
                                                    size="xs"
													class="text-primary/40 hover:text-primary hover:bg-primary/10"
													onclick={(e) => { e.stopPropagation(); infoProductId = prod.id; }}
												>
                                                    <svelte:fragment slot="icon">
													    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-3.5 h-3.5"><path stroke-linecap="round" stroke-linejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" /></svg>
                                                    </svelte:fragment>
												</Button>
											{/if}
										</div>
									</div>
								</div>
							</button>

							{#if infoProductId === prod.id}
								<div 
									class="absolute inset-0 z-10 bg-base-100/95 backdrop-blur-md rounded-2xl p-4 flex flex-col items-center justify-center text-center shadow-2xl border-2 border-primary/20 pointer-events-auto"
									onclick={(e) => { e.stopPropagation(); infoProductId = null; }}
                                    aria-hidden="true"
									transition:fade={{ duration: 150 }}
								>
									<div 
										class="flex flex-col items-center justify-center h-full w-full"
										in:scale={{ duration: 200, start: 0.95 }}
									>
										<div class="absolute top-2 right-2">
											<Button variant="ghost" circle size="xs" class="text-base-content/40">
												<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
											</Button>
										</div>
										<h4 class="font-black text-xs uppercase tracking-widest text-primary mb-2 line-clamp-1">{prod.name}</h4>
										<div class="flex-1 overflow-y-auto w-full px-2 elegant-scroll">
											<p class="text-[11px] leading-relaxed opacity-90 text-left">
												{prod.description}
											</p>
										</div>
										<div class="mt-3 text-[9px] font-bold uppercase tracking-tighter opacity-30 animate-pulse">Tocar para cerrar</div>
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
	.tabs-box::-webkit-scrollbar {
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
