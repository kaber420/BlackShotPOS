<script lang="ts">
	import { onMount } from 'svelte';
	import { fetchApi } from '$lib/api';
	import { ProductService, type Product } from '$lib/api/products';
	import { CategoryService, type Category } from '$lib/api/categories';
	import { appState, addToCart, removeFromCart, clearCart, setActiveTable } from '$lib/app_state.svelte';
	import ProductCustomizer from '$lib/components/ProductCustomizer.svelte';

	let categories = $state<Category[]>([]);
	let products = $state<Product[]>([]);
	let selectedCategory = $state<number | null>(null);
	let isLoading = $state(true);

	// Modal State
	let showCustomizer = $state(false);
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
		} catch (e) {
			console.error("Error loading initial data", e);
		} finally {
			isLoading = false;
		}
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

	let cartTotal = $derived(appState.cart.reduce((acc, item) => acc + item.total_price, 0));
	let taxTotal = $derived(cartTotal * 0.16);
	let finalTotal = $derived(cartTotal + taxTotal);

	async function processCheckout() {
		if (appState.cart.length === 0) return;
		
		try {
			// 1. Get or Create order
            let order;
            if (appState.activeOrder) {
                order = appState.activeOrder;
            } else {
    			order = await fetchApi<any>('/api/v1/pos/orders', {
	    			method: 'POST',
		    		body: JSON.stringify({ type: 'TAKEAWAY' })
			    });
            }

			// 2. Add items
			for (const item of appState.cart) {
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

			// 3. Mark as PAID (Simulated checkout)
			await fetchApi(`/api/v1/pos/orders/${order.id}/status?status=PAID`, {
				method: 'PATCH'
			});

			alert("Venta realizada con éxito!");
			clearCart();
            setActiveTable(null);
		} catch (e) {
			alert(`Error al procesar: ${e}`);
		}
	}
</script>

<div class="p-4 md:p-6 lg:p-8 flex flex-col gap-6 h-full">
	<!-- Top Stats Row (Visual Only for now) -->
	<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
		<div class="stat bg-base-100 rounded-box shadow-sm border border-base-200">
			<div class="stat-title">Ventas Hoy</div>
			<div class="stat-value text-primary font-serif">$4,200.00</div>
			<div class="stat-desc">Actualizado hace un momento</div>
		</div>
		<div class="stat bg-base-100 rounded-box shadow-sm border border-base-200">
			<div class="stat-title">Tickets Abiertos</div>
			<div class="stat-value text-secondary">8</div>
			<div class="stat-desc">Operación normal</div>
		</div>
		<div class="stat bg-base-100 rounded-box shadow-sm border border-base-200">
			<div class="stat-title">Producto Estrella</div>
			<div class="stat-value text-accent text-3xl font-bold">Latte Vainilla</div>
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
							class="card bg-base-100 shadow-sm hover:shadow-md transition-all active:scale-95 border border-base-200 hover:border-primary cursor-pointer text-left h-40 flex flex-col group overflow-hidden"
							onclick={() => handleProductClick(prod)}
						>
							<div class="h-24 w-full bg-base-200 relative">
								{#if prod.image_url}
									<img src={prod.image_url} alt={prod.name} class="w-full h-full object-cover group-hover:scale-105 transition-transform" />
								{/if}
								<div class="absolute top-2 right-2 badge badge-ghost">${prod.price}</div>
							</div>
							<div class="p-3 flex-1 flex flex-col justify-center">
								<h3 class="font-bold text-xs uppercase tracking-tight leading-tight line-clamp-2">{prod.name}</h3>
							</div>
						</button>
					{/each}
				{/if}
			</div>
		</div>

		<!-- Right: Current Ticket (30%) -->
		<div class="w-full lg:w-1/3 bg-base-100 rounded-xl shadow-sm flex flex-col h-full border border-base-200">
			<div class="p-4 border-b border-base-200 bg-base-200/30 rounded-t-xl">
				<div class="flex justify-between items-center">
					<h2 class="font-bold text-lg uppercase tracking-widest text-primary">Ticket</h2>
					<button class="btn btn-ghost btn-xs text-error" onclick={() => { clearCart(); setActiveTable(null); }}>Limpiar</button>
				</div>
				<p class="text-[10px] opacity-70">
                    {appState.activeTable ? `MESA ${appState.activeTable.number} - SERVICIO COMEDOR` : 'PARA LLEVAR - CLIENTE MOSTRADOR'}
                </p>
			</div>
			
			<!-- Items in Cart -->
			<div class="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
				{#if appState.cart.length === 0}
					<div class="flex flex-col items-center justify-center h-full opacity-20 py-10">
						<svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
						</svg>
						<p class="mt-2 font-bold">Ticket Vacío</p>
					</div>
				{:else}
					{#each appState.cart as item (item.id)}
						<div class="flex justify-between items-start bg-base-200/40 p-3 rounded-lg border border-base-200/50">
							<div class="flex flex-col flex-1">
								<span class="font-bold text-sm uppercase">{item.name}</span>
								{#each item.modifiers as mod}
									<span class="text-[10px] opacity-60 leading-none mt-1">+ {mod.name}</span>
								{/each}
							</div>
							<div class="flex items-center gap-3">
								<span class="font-bold text-sm text-primary">${item.total_price.toFixed(2)}</span>
								<button class="btn btn-circle btn-xs btn-error btn-outline border-none" onclick={() => removeFromCart(item.id)}>×</button>
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
					<span class="text-3xl font-black text-primary font-serif">${finalTotal.toFixed(2)}</span>
				</div>
				
				<button 
					class="btn btn-primary w-full btn-lg shadow-lg shadow-primary/20" 
					disabled={appState.cart.length === 0}
					onclick={processCheckout}
				>
					Cobrar ${finalTotal.toFixed(2)}
				</button>
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
</style>
