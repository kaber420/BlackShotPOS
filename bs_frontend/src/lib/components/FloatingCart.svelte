<!-- FloatingCart.svelte -->
<script lang="ts">
	import { slide, fade, fly } from 'svelte/transition';
	import { appState, removeFromCart, clearCart, setActiveTable } from '$lib/app_state.svelte';
	import { fetchApi } from '$lib/api';
	import { OrderService } from '$lib/api/orders';
	import { addToast } from '$lib/toast.svelte.js';
    import PaymentModal from '$lib/components/PaymentModal.svelte';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import Button from '$lib/components/ui/Button.svelte';

	let showPaymentModal = $state(false);
	let isLoading = $state(false);

	let cartTotal = $derived(appState.cart.reduce((acc, item) => acc + item.total_price, 0));
	let taxTotal = $derived(cartTotal * (appState.settings?.tax_rate || 0.16));
	let finalTotal = $derived(cartTotal + taxTotal);
	let itemCount = $derived(appState.cart.length);

	let previousItemCount = $state(0);
	$effect(() => {
		if (itemCount > previousItemCount) {
			appState.cartVisible = true;
		}
		previousItemCount = itemCount;
	});

	function toggleCart() {
		appState.cartVisible = !appState.cartVisible;
	}

	function openCheckout() {
		if (itemCount === 0) return;
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

			addToast("¡Venta realizada con éxito!", "success");
            showPaymentModal = false;
            appState.cartVisible = false;
			clearCart();
            
            const wasTable = appState.activeTable;
            setActiveTable(null);
            
            if (page.url.pathname === '/orders') {
                // Do nothing, stay on orders page
            } else if (page.url.searchParams.has('order_id')) {
                goto('/', { replaceState: true });
            } else if (wasTable && page.url.pathname !== '/tables') {
                goto('/tables');
            }
		} catch (e) {
			addToast(`Error al procesar: ${e}`, "error");
		} finally {
            isLoading = false;
        }
	}

    async function sendToKitchen() {
        if (appState.cart.length === 0) return;
        
        try {
            isLoading = true;
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

            for (const item of appState.cart) {
                if (item.db_id) continue;
                
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

            addToast("¡Comanda enviada a cocina!", "success");
            clearCart();
            appState.cartVisible = false;
            
            if (appState.activeTable) {
                setActiveTable(null);
                goto('/tables');
            }
        } catch (e) {
            addToast(`Error al enviar a cocina: ${e}`, "error");
        } finally {
            isLoading = false;
        }
    }
</script>

{#if itemCount > 0}
	<!-- Collapsed Floating Button / Bar -->
	{#if !appState.cartVisible}
		<div
			class="fixed bottom-4 right-4 z-40"
			in:fly={{ y: 50, duration: 300 }}
			out:fade={{ duration: 150 }}
		>
			<Button
				variant="primary"
				size="lg"
				class="shadow-xl shadow-primary/30 flex items-center gap-3 rounded-full pl-4 pr-6"
				onclick={toggleCart}
			>
                <div class="indicator">
                    <span class="indicator-item badge badge-secondary font-black scale-110">{itemCount}</span>
                    <div class="bg-primary-content text-primary p-2 rounded-full hidden md:block">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
                        </svg>
                    </div>
                </div>
				<div class="flex flex-col items-start ml-2 md:ml-0">
					<span class="font-bold text-xs uppercase tracking-wider opacity-90 hidden md:block">Ver Pedido</span>
					<span class="font-black text-lg md:text-xl">{appState.settings?.currency_symbol}{finalTotal.toFixed(2)}</span>
				</div>
			</Button>
		</div>
	{/if}

	<!-- Expanded Floating Panel -->
	{#if appState.cartVisible}
        <!-- Backdrop for mobile overlay, clicking it closes the cart -->
        <div 
            class="fixed inset-0 bg-base-300/40 backdrop-blur-sm z-40 lg:hidden" 
            transition:fade={{ duration: 200 }}
            onclick={toggleCart}
            aria-hidden="true"
        ></div>

		<!-- Mobile: Full Screen Drawer / Desktop: Side Floating Panel -->
		<div
			class="fixed bottom-0 right-0 top-0 left-0 lg:left-auto lg:w-[400px] lg:m-4 lg:bottom-auto lg:h-[calc(100vh-2rem)] lg:rounded-2xl bg-base-100 shadow-2xl flex flex-col border border-base-200 z-50 overflow-hidden"
			in:fly={{ x: 100, duration: 300 }}
			out:fade={{ duration: 200 }}
		>
			<div class="flex justify-between items-center p-4 border-b border-base-200 bg-base-200/30 shrink-0">
                <div class="flex items-center gap-3">
                    <h2 class="font-black text-lg uppercase tracking-widest text-primary flex items-center gap-2">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
                        </svg>
                        Pedido
                    </h2>
                    {#if appState.activeTable}
                        <div class="badge badge-secondary font-black shadow-sm">
                            Mesa {appState.activeTable.number}
                        </div>
                    {:else}
                        <div class="badge badge-ghost font-bold opacity-70">
                            PARA LLEVAR
                        </div>
                    {/if}
                </div>
				<Button variant="ghost" circle size="sm" onclick={toggleCart} aria-label="Cerrar pedido">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </Button>
			</div>
			
			<!-- Items in Cart -->
			<div class="flex-1 overflow-y-auto p-4 flex flex-col gap-3 min-h-0">
                <div class="flex justify-between items-center mb-2">
                    <span class="text-xs font-bold opacity-50 uppercase">{itemCount} items</span>
                    <Button variant="ghost" size="xs" danger onclick={() => { clearCart(); setActiveTable(null); appState.cartVisible = false; }}>
                        Vaciar Todo
                    </Button>
                </div>
					{#each appState.cart as item (item.id)}
						<div class="flex justify-between items-start {item.db_id ? 'bg-base-300/20 opacity-70' : 'bg-base-200/40'} p-3 rounded-lg border {item.db_id ? 'border-base-300' : 'border-base-200/50'}">
							<div class="flex flex-col flex-1 pl-1 pr-2">
                                <div class="flex items-center gap-2 flex-wrap">
    								<span class="font-bold text-sm uppercase leading-tight {item.status === 'CANCELLED' ? 'line-through text-error' : ''}">
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
							<div class="flex flex-col items-end gap-1">
								<span class="font-bold text-sm {item.db_id ? 'opacity-50' : 'text-primary'}">${item.total_price.toFixed(2)}</span>
                                {#if !item.db_id}
								    <Button variant="ghost" size="xs" danger circle onclick={() => removeFromCart(item.id)}>×</Button>
                                {/if}
							</div>
						</div>
					{/each}
			</div>

			<!-- Cart Totals & Pay Button -->
			<div class="p-4 border-t border-base-200 bg-base-200/20 pb-safe shrink-0">
				<div class="flex justify-between mb-1 text-xs opacity-70 uppercase font-medium">
					<span>Subtotal</span>
					<span>${cartTotal.toFixed(2)}</span>
				</div>
				<div class="flex justify-between mb-3 text-xs opacity-70 uppercase font-medium">
					<span>IVA ({appState.settings?.tax_rate ? (appState.settings.tax_rate * 100).toFixed(0) : 16}%)</span>
					<span>${taxTotal.toFixed(2)}</span>
				</div>
				<div class="flex justify-between mb-4 items-end">
					<span class="text-sm font-bold opacity-60 uppercase">Total Cobrar</span>
					<span class="text-3xl font-black text-primary font-serif">{appState.settings?.currency_symbol}{finalTotal.toFixed(2)}</span>
				</div>
				
				<div class="flex flex-col gap-2 relative">
                    <Button 
                        variant="primary" 
                        size="lg" 
                        class="w-full shadow-lg shadow-primary/20" 
                        disabled={appState.cart.length === 0}
                        {isLoading}
                        onclick={openCheckout}
                    >
                        Cobrar {appState.settings?.currency_symbol}{finalTotal.toFixed(2)}
                    </Button>

                    <Button 
                        variant="outline"
                        size="lg" 
                        class="w-full" 
                        disabled={appState.cart.length === 0}
                        {isLoading}
                        onclick={sendToKitchen}
                    >
                        <svelte:fragment slot="icon">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5"><path stroke-linecap="round" stroke-linejoin="round" d="M15.362 5.214A8.252 8.252 0 0112 21 8.25 8.25 0 016.038 7.048 8.287 8.287 0 009 9.6a8.983 8.983 0 013.361-6.867 8.21 8.21 0 003 2.48z" /><path stroke-linecap="round" stroke-linejoin="round" d="M12 18a3.75 3.75 0 00.495-7.467 5.99 5.99 0 00-1.925 3.546 5.974 5.974 0 01-1.333-1.756A3.75 3.75 0 0012 18z" /></svg>
                        </svelte:fragment>
                        Enviar a Cocina
                    </Button>
                </div>
			</div>
		</div>
	{/if}
{/if}

<PaymentModal 
    isOpen={showPaymentModal}
    total={finalTotal}
    onClose={() => showPaymentModal = false}
    onConfirm={processCheckout}
/>

<style>
    /* Prevent body scroll when mobile cart is open */
    :global(body:has(.fixed.inset-0)) {
        overflow: hidden;
    }
    
    /* Support for safe area insets on mobile iOS devices */
    .pb-safe {
        padding-bottom: env(safe-area-inset-bottom, 1rem);
    }
</style>
