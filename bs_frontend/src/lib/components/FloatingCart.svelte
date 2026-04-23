<!-- FloatingCart.svelte -->
<script lang="ts">
	import { slide, fade, fly } from 'svelte/transition';
	import { appState, removeFromCart, clearCart, setActiveTable, updateCartItemQuantity } from '$lib/app_state.svelte';
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

	async function processCheckout(method: string, amount: number, shouldPrint: boolean, vacateTable: boolean) {
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
            await OrderService.pay(order.id, method, amount, vacateTable);

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
			
			<div class="flex-1 overflow-y-auto p-5 flex flex-col gap-4 min-h-0 elegant-scroll bg-base-200/30">
                <div class="flex justify-between items-center px-1">
                    <span class="text-[10px] font-black opacity-40 uppercase tracking-[0.2em]">{itemCount} Artículos en Pedido</span>
                    <button class="text-[10px] font-black text-error/60 hover:text-error uppercase tracking-widest transition-colors" onclick={() => { clearCart(); setActiveTable(null); appState.cartVisible = false; }}>
                        Vaciar Todo
                    </button>
                </div>

					{#each appState.cart as item (item.id)}
						<div class="flex flex-col gap-3 p-4 rounded-[1.5rem] bg-base-100 border border-base-200 shadow-sm transition-all hover:shadow-md {item.db_id ? 'opacity-80 grayscale-[0.3]' : ''}">
							<div class="flex justify-between items-start">
                                <div class="flex flex-col gap-1 flex-1">
    								<span class="font-black text-sm uppercase leading-tight tracking-tight {item.status === 'CANCELLED' ? 'line-through text-error' : 'text-base-content'}">
                                        {item.name}
                                    </span>
                                    {#if item.status || item.db_id}
                                        <div class="flex gap-1">
                                            {#if item.status === 'CANCELLED'}
                                                <span class="badge badge-error badge-xs text-[8px] font-black tracking-tighter uppercase px-1">ANULADO</span>
                                            {:else if item.status === 'READY'}
                                                <span class="badge badge-success badge-xs text-[8px] font-black tracking-tighter uppercase px-1">LISTO</span>
                                            {:else if item.status === 'PREPARANDO'}
                                                <span class="badge badge-primary badge-xs text-[8px] font-black tracking-tighter uppercase px-1">EN COCINA</span>
                                            {:else if item.db_id}
                                                <span class="badge badge-ghost badge-xs text-[8px] font-black tracking-tighter uppercase px-1">EN COLA</span>
                                            {/if}
                                        </div>
                                    {/if}
                                </div>
                                <span class="font-mono font-black text-sm text-primary tracking-tighter">${item.total_price.toFixed(0)}</span>
                            </div>

                            {#if item.modifiers.length > 0}
                                <div class="flex flex-wrap gap-1.5 border-t border-base-200/50 pt-2 opacity-60">
                                    {#each item.modifiers as mod}
                                        <span class="text-[9px] font-bold uppercase bg-base-200 px-2 py-0.5 rounded-full">+ {mod.name}</span>
                                    {/each}
                                </div>
                            {/if}

                            <div class="flex justify-between items-center mt-1">
                                {#if !item.db_id}
                                    <!-- Quantity Selector Premium -->
                                    <div class="flex items-center bg-base-200/50 rounded-full p-1 gap-3">
                                        <button 
                                            class="w-7 h-7 flex items-center justify-center bg-white rounded-full shadow-sm text-primary hover:bg-primary hover:text-white transition-all active:scale-90 font-black"
                                            onclick={() => updateCartItemQuantity(item.id, -1)}
                                            title="Reducir cantidad"
                                        >
                                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="3" stroke="currentColor" class="w-3 h-3" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 12h-15" /></svg>
                                        </button>
                                        <span class="font-black text-sm w-4 text-center">{item.quantity}</span>
                                        <button 
                                            class="w-7 h-7 flex items-center justify-center bg-white rounded-full shadow-sm text-primary hover:bg-primary hover:text-white transition-all active:scale-90 font-black"
                                            onclick={() => updateCartItemQuantity(item.id, 1)}
                                            title="Aumentar cantidad"
                                        >
                                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="3" stroke="currentColor" class="w-3 h-3" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
                                        </button>
                                    </div>
                                    
                                    <button 
                                        class="text-[10px] font-black text-error/40 hover:text-error transition-colors uppercase tracking-widest px-2"
                                        onclick={() => removeFromCart(item.id)}
                                    >
                                        Eliminar
                                    </button>
                                {:else}
                                    <span class="text-[9px] font-black opacity-30 uppercase tracking-widest italic ml-auto">Enviado</span>
                                {/if}
                            </div>
						</div>
					{/each}
			</div>

			<!-- Cart Totals & Pay Button -->
			<div class="p-6 lg:p-8 border-t border-base-200 bg-base-100 pb-safe shrink-0 shadow-[0_-10px_30px_-15px_rgba(0,0,0,0.05)]">
				<div class="flex justify-between mb-2 text-[10px] opacity-40 uppercase font-black tracking-widest">
					<span>Subtotal</span>
					<span class="font-mono">${cartTotal.toFixed(0)}</span>
				</div>
				<div class="flex justify-between mb-4 text-[10px] opacity-40 uppercase font-black tracking-widest">
					<span>IVA ({appState.settings?.tax_rate ? (appState.settings.tax_rate * 100).toFixed(0) : 16}%)</span>
					<span class="font-mono">${taxTotal.toFixed(0)}</span>
				</div>
				<div class="flex justify-between mb-8 items-end border-b border-base-200 pb-4">
					<span class="text-xs font-black opacity-60 uppercase tracking-[0.2em]">Total a Pagar</span>
					<span class="text-4xl font-black text-primary font-mono tracking-tighter">{appState.settings?.currency_symbol}{finalTotal.toFixed(0)}</span>
				</div>
				
				<div class="flex flex-col gap-3 relative mb-2">
                    <button 
                        class="w-full bg-primary hover:bg-primary/90 text-white rounded-2xl py-5 px-6 font-black uppercase tracking-[0.1em] text-lg shadow-xl shadow-primary/20 transition-all active:scale-[0.98] disabled:opacity-50 flex items-center justify-center gap-3 group"
                        disabled={appState.cart.length === 0 || isLoading}
                        onclick={openCheckout}
                    >
                        {#if isLoading}
                            <span class="loading loading-spinner loading-md"></span>
                        {:else}
                            <span>Cobrar Orden</span>
                            <span class="w-1.5 h-1.5 rounded-full bg-white/40 group-hover:scale-150 transition-transform"></span>
                            <span class="font-mono">${finalTotal.toFixed(0)}</span>
                        {/if}
                    </button>

                    <button 
                        class="w-full bg-base-200 hover:bg-base-300 text-base-content/70 rounded-2xl py-4 px-6 font-black uppercase tracking-[0.1em] text-xs transition-all active:scale-[0.98] disabled:opacity-50 flex items-center justify-center gap-2"
                        disabled={appState.cart.length === 0 || isLoading}
                        onclick={sendToKitchen}
                    >
                        {#if isLoading}
                            <span class="loading loading-spinner loading-xs"></span>
                        {:else}
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="3" stroke="currentColor" class="w-4 h-4"><path stroke-linecap="round" stroke-linejoin="round" d="M15.362 5.214A8.252 8.252 0 0112 21 8.25 8.25 0 016.038 7.048 8.287 8.287 0 009 9.6a8.983 8.983 0 013.361-6.867 8.21 8.21 0 003 2.48z" /><path stroke-linecap="round" stroke-linejoin="round" d="M12 18a3.75 3.75 0 00.495-7.467 5.99 5.99 0 00-1.925 3.546 5.974 5.974 0 01-1.333-1.756A3.75 3.75 0 0012 18z" /></svg>
                            Enviar a Cocina
                        {/if}
                    </button>
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
    hasTable={!!appState.activeTable}
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
