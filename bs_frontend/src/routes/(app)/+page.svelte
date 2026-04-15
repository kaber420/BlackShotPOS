<script lang="ts">
	import { onMount } from 'svelte';
	import { fetchApi } from '$lib/api';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
	import { ProductService, type Product } from '$lib/api/products';
	import { CategoryService, type Category } from '$lib/api/categories';
	import { OrderService, OrderStatus } from '$lib/api/orders';
	import { appState, addToCart, removeFromCart, clearCart, setActiveTable, loadOrderToCart } from '$lib/app_state.svelte';
	import ProductCustomizer from '$lib/components/ProductCustomizer.svelte';
	import PaymentModal from '$lib/components/PaymentModal.svelte';

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
    let showPaymentModal = $state(false);
	let activeProduct = $state<any>(null);

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

	let cartTotal = $derived(appState.cart.reduce((acc, item) => acc + item.total_price, 0));
	let taxTotal = $derived(cartTotal * (appState.settings.tax_rate || 0.16));
	let finalTotal = $derived(cartTotal + taxTotal);

    function openCheckout() {
        if (appState.cart.length === 0) return;
        showPaymentModal = true;
    }

	async function processCheckout(method: string, amount: number, shouldPrint: boolean) {
		if (appState.cart.length === 0) return;
		
		try {
            isLoading = true;
			// 1. Get or Create order
            let order;
            if (appState.activeOrder) {
                order = appState.activeOrder;
            } else {
                const orderPayload = {
                    type: appState.activeTable ? 'DINE_IN' : 'TAKEAWAY',
                    table_id: appState.activeTable ? appState.activeTable.id : null
                };
    			order = await fetchApi<any>('/api/v1/pos/orders', {
	    			method: 'POST',
		    		body: JSON.stringify(orderPayload)
			    });
            }

			// 2. Add New items only (those without db_id)
			for (const item of appState.cart) {
                if (!item.db_id) {
    				await fetchApi(`/api/v1/pos/orders/${order.id}/items`, {
	    				method: 'POST',
		    			body: JSON.stringify({
			    			product_id: item.product_id,
				    		product_variant_id: item.product_variant_id,
					    	quantity: item.quantity,
						    modifier_ids: item.modifiers.map((m: any) => m.id)
    					})
	    			});
                }
			}

            // 3. Register payment (will set is_paid = true in backend)
            await OrderService.pay(order.id, method, amount);

            // 4. Print ticket if requested
            if (shouldPrint) {
                try {
                    await fetchApi(`/api/v1/pos/print/ticket/${order.id}/network`, { method: 'POST' });
                } catch (pe) {
                    console.error("Error al imprimir ticket", pe);
                }
            }

			alert("¡Venta realizada con éxito!");
            showPaymentModal = false;
			clearCart();
            
            // Guardar referencia a la mesa para la redirección
            const wasTable = appState.activeTable;
            setActiveTable(null);
            
            // Si veníamos de una orden específica, limpiar URL
            if (page.url.searchParams.has('order_id')) {
                goto('/', { replaceState: true });
            } else if (wasTable) {
                goto('/tables');
            }
		} catch (e) {
			alert(`Error al procesar: ${e}`);
		} finally {
            isLoading = false;
        }
	}

    async function sendToKitchen() {
        if (appState.cart.length === 0) return;
        
        try {
            isLoading = true;
            // 1. Obtener o crear orden
            let order;
            if (appState.activeOrder) {
                order = appState.activeOrder;
            } else {
                const orderPayload = {
                    type: appState.activeTable ? 'DINE_IN' : 'TAKEAWAY',
                    table_id: appState.activeTable ? appState.activeTable.id : null
                };
                order = await fetchApi<any>('/api/v1/pos/orders', {
                    method: 'POST',
                    body: JSON.stringify(orderPayload)
                });
            }

            // 2. Añadir SOLO items nuevos al backend
            for (const item of appState.cart) {
                if (item.db_id) continue; // Saltar items que ya están en la base de datos
                
                await fetchApi(`/api/v1/pos/orders/${order.id}/items`, {
                    method: 'POST',
                    body: JSON.stringify({
                        product_id: item.product_id,
                        product_variant_id: item.product_variant_id,
                        quantity: item.quantity,
                        modifier_ids: item.modifiers.map((m: any) => m.id)
                    })
                });
            }

            // 3. El estado se mantiene en PENDING para que cocina lo inicie manualmente

            alert("¡Comanda enviada a cocina!");
            clearCart();
            
            // Si era una mesa, volver al tablero de mesas
            if (appState.activeTable) {
                setActiveTable(null);
                goto('/tables');
            }
        } catch (e) {
            alert(`Error al enviar a cocina: ${e}`);
        } finally {
            isLoading = false;
        }
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
	<div class="flex flex-col lg:flex-row gap-6 h-[72vh]">
		
		<!-- Left: Categories & Products (70%) -->
		<div class="w-full lg:w-2/3 flex flex-col gap-4">
			<!-- Categories Tabs -->
			<div class="tabs tabs-box bg-base-100 shadow-sm p-1 rounded-lg border border-base-200 overflow-x-auto whitespace-nowrap">
				{#each categories as cat}
					<button 
						role="tab" 
						class="tab {selectedCategory === (cat.id ?? null) ? 'tab-active' : ''}"
						onclick={() => loadProducts(cat.id ?? null)}
					>
						{cat.name}
					</button>
				{/each}
			</div>
			
			<!-- Product Grid -->
			<div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4 overflow-y-auto pb-4 pr-2">
				{#if isLoading}
					<div class="col-span-full flex justify-center py-20">
						<span class="loading loading-spinner loading-lg text-primary"></span>
					</div>
				{:else}
					{#each products as prod}
						<button 
							class="card group relative bg-base-100 border border-base-200 rounded-3xl overflow-hidden transition-all duration-500 text-left h-auto {prod.is_active ? 'hover:shadow-2xl hover:shadow-primary/5 hover:-translate-y-1 cursor-pointer active:scale-95' : 'opacity-70 grayscale-[0.5] cursor-not-allowed'}"
							onclick={() => prod.is_active && handleProductClick(prod)}
						>
							<div class="aspect-[4/3] w-full relative overflow-hidden bg-base-200">
								{#if prod.image_url}
									<img src={prod.image_url} alt={prod.name} class="w-full h-full object-cover transition-transform duration-700 {prod.is_active ? 'group-hover:scale-110' : ''}" />
                                {:else}
                                    <div class="w-full h-full flex items-center justify-center bg-gradient-to-br from-primary/5 to-primary/10">
                                        <span class="text-5xl font-black text-primary/20 opacity-30 select-none">
                                            {prod.name.charAt(0).toUpperCase()}
                                        </span>
                                    </div>
								{/if}

								{#if !prod.is_active}
                                    <div class="absolute inset-0 bg-base-300/60 backdrop-blur-[2px] flex items-center justify-center p-6">
                                        <div class="bg-base-100/90 text-base-content px-4 py-2 rounded-xl shadow-xl border border-base-300 transform -rotate-3 font-black uppercase tracking-tighter text-xs">
                                            No Disponible
                                        </div>
                                    </div>
								{/if}
							</div>
							<div class="p-4 flex-1 flex flex-col justify-start">
								<h3 class="text-lg font-bold leading-tight group-hover:text-primary transition-colors mb-2 line-clamp-2">{prod.name}</h3>
                                <div class="flex flex-wrap items-center gap-2 mt-auto">
                                    {#if prod.variants && prod.variants.length > 0}
                                        {#each prod.variants as variant}
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
                                    {:else if prod.price && prod.price >= 0}
                                        <span class="text-xl font-black text-base-content/90 font-mono tracking-tighter">
                                            ${prod.price.toFixed(0)}
                                        </span>
                                    {/if}
                                </div>
							</div>
						</button>
					{/each}
				{/if}
			</div>
		</div>

		<!-- Right: Current Pedido (30%) -->
		<div class="w-full lg:w-1/3 bg-base-100 rounded-xl shadow-sm flex flex-col h-full border border-base-200">
			<div class="p-4 border-b border-base-200 bg-base-200/30 rounded-t-xl">
				<div class="flex justify-between items-center">
					<div class="flex items-center gap-3">
						<h2 class="font-bold text-lg uppercase tracking-widest text-primary">Pedido</h2>
						{#if appState.activeTable}
							<div class="badge badge-secondary badge-lg font-black px-4 py-4 h-auto shadow-sm">
								<div class="flex flex-col items-start leading-tight">
									<span class="text-[9px] opacity-80 uppercase tracking-tighter">Mesa</span>
									<span class="text-base">{appState.activeTable.number}</span>
								</div>
							</div>
						{:else}
							<div class="badge badge-ghost badge-lg font-bold px-4 py-4 h-auto opacity-70">
								<div class="flex flex-col items-start leading-tight">
									<span class="text-[9px] opacity-60 uppercase tracking-tighter">Tipo</span>
									<span class="text-sm">PARA LLEVAR</span>
								</div>
							</div>
						{/if}
					</div>
					<button class="btn btn-ghost btn-xs text-error" onclick={() => { clearCart(); setActiveTable(null); }}>Limpiar</button>
				</div>
			</div>
			
			<!-- Items in Cart -->
			<div class="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
				{#if appState.cart.length === 0}
					<div class="flex flex-col items-center justify-center h-full opacity-20 py-10">
						<svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
						</svg>
						<p class="mt-2 font-bold">Pedido Vacío</p>
					</div>
				{:else}
					{#each appState.cart as item (item.id)}
						<div class="flex justify-between items-start {item.db_id ? 'bg-base-300/20 opacity-70' : 'bg-base-200/40'} p-3 rounded-lg border {item.db_id ? 'border-base-300' : 'border-base-200/50'}">
							<div class="flex flex-col flex-1">
                                <div class="flex items-center gap-2">
    								<span class="font-bold text-sm uppercase {item.status === 'CANCELLED' ? 'line-through text-error' : ''}">
                                        {item.name}
                                    </span>
                                    {#if item.status === 'CANCELLED'}
                                        <span class="badge badge-error badge-xs text-[8px] font-black tracking-tighter uppercase px-1">ANULADO</span>
                                    {:else if item.status === 'READY'}
                                        <span class="badge badge-success badge-xs text-[8px] font-black tracking-tighter uppercase px-1">LISTO</span>
                                    {:else if item.status === 'PREPARANDO'}
                                        <span class="badge badge-primary badge-xs text-[8px] font-black tracking-tighter uppercase px-1 animated-pulse">COCINANDO</span>
                                    {:else if item.db_id}
                                        <span class="badge badge-ghost badge-xs text-[8px] font-black tracking-tighter uppercase px-1">EN COLA</span>
                                    {/if}
                                </div>
								{#each item.modifiers as mod}
									<span class="text-[10px] opacity-60 leading-none mt-1">+ {mod.name}</span>
								{/each}
							</div>
							<div class="flex items-center gap-3">
								<span class="font-bold text-sm {item.db_id ? 'opacity-50' : 'text-primary'}">${item.total_price.toFixed(2)}</span>
                                {#if !item.db_id}
								    <button class="btn btn-circle btn-xs btn-error btn-outline border-none" onclick={() => removeFromCart(item.id)}>×</button>
                                {/if}
							</div>
						</div>
					{/each}
				{/if}
			</div>

			<!-- Cart Totals & Pay Button -->
			<div class="p-4 border-t border-base-200 bg-base-200/20 rounded-b-xl">
				<div class="flex justify-between mb-1 text-xs opacity-70 uppercase font-medium">
					<span>Subtotal</span>
					<span>${cartTotal.toFixed(2)}</span>
				</div>
				<div class="flex justify-between mb-3 text-xs opacity-70 uppercase font-medium">
					<span>IVA (16%)</span>
					<span>${taxTotal.toFixed(2)}</span>
				</div>
				<div class="flex justify-between mb-4 items-end">
					<span class="text-sm font-bold opacity-60 uppercase">Total Cobrar</span>
					<span class="text-3xl font-black text-primary font-serif">{appState.settings.currency_symbol}{finalTotal.toFixed(2)}</span>
				</div>
				
				<div class="flex flex-col gap-2">
                    <button 
                        class="btn btn-primary w-full shadow-lg shadow-primary/20" 
                        disabled={appState.cart.length === 0 || isLoading}
                        onclick={openCheckout}
                    >
                        {#if isLoading}
                            <span class="loading loading-spinner loading-xs"></span>
                        {:else}
                            Cobrar {appState.settings.currency_symbol}{finalTotal.toFixed(2)}
                        {/if}
                    </button>

                    <button 
                        class="btn btn-outline btn-secondary w-full" 
                        disabled={appState.cart.length === 0 || isLoading}
                        onclick={sendToKitchen}
                    >
                        {#if isLoading}
                            <span class="loading loading-spinner loading-xs"></span>
                        {:else}
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5"><path stroke-linecap="round" stroke-linejoin="round" d="M15.362 5.214A8.252 8.252 0 0112 21 8.25 8.25 0 016.038 7.048 8.287 8.287 0 009 9.6a8.983 8.983 0 013.361-6.867 8.21 8.21 0 003 2.48z" /><path stroke-linecap="round" stroke-linejoin="round" d="M12 18a3.75 3.75 0 00.495-7.467 5.99 5.99 0 00-1.925 3.546 5.974 5.974 0 01-1.333-1.756A3.75 3.75 0 0012 18z" /></svg>
                            Enviar a Cocina
                        {/if}
                    </button>
                </div>
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

<PaymentModal 
    isOpen={showPaymentModal}
    total={finalTotal}
    onClose={() => showPaymentModal = false}
    onConfirm={processCheckout}
/>

<style>
	.tabs-box::-webkit-scrollbar {
		display: none;
	}
</style>
