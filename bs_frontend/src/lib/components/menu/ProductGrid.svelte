<script lang="ts">
	import type { Product } from '$lib/api/products';
	import type { Category } from '$lib/api/categories';
	import Button from '$lib/components/ui/Button.svelte';

	interface Props {
		products: Product[];
		categories: Category[];
		onEdit: (product: Product) => void;
		onDelete: (id: number) => void;
	}

	let { products, categories, onEdit, onDelete } = $props<Props>();

	function getCategoryName(id?: number) {
		if (!id) return 'Sin categoría';
		return categories.find(c => c.id === id)?.name || 'Categoría desconocida';
	}
</script>

<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-6">
	{#each products as product (product.id)}
		<div class="bg-base-100 p-6 rounded-3xl border border-base-200 shadow-sm hover:shadow-md hover:-translate-y-1 transition-all duration-300 group flex flex-col gap-5 min-h-[220px]">
			<div class="flex justify-between items-start">
				<div class="flex items-center gap-4">
					<div class="avatar placeholder shrink-0">
						<div class="bg-primary/10 text-primary rounded-2xl w-16 h-16 border border-primary/20 shadow-inner">
							{#if product.image_url}
								<img src={product.image_url} alt={product.name} class="object-cover" />
							{:else}
								<span class="text-lg font-black">{product.name.substring(0, 2).toUpperCase()}</span>
							{/if}
						</div>
					</div>
					<div class="flex flex-col min-w-0">
						<h3 class="font-black text-xl tracking-tight truncate leading-tight">{product.name}</h3>
						<span class="badge badge-ghost badge-xs font-black text-[9px] uppercase tracking-wider w-fit mt-1 border-none bg-base-200">
							{getCategoryName(product.category_id)}
						</span>
					</div>
				</div>
				<div class="flex gap-2 shrink-0">
					<!-- Edit Button -->
					<Button 
						variant="ghost" 
						square 
						size="sm" 
						class="bg-base-200 hover:bg-base-300 transition-colors rounded-xl"
						onclick={() => onEdit(product)} 
						title="Editar"
					>
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-4 h-4">
							<path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
						</svg>
					</Button>

					<!-- Delete Button (The "basurita" black button) -->
					<Button 
						variant="ghost" 
						square 
						size="sm" 
						class="bg-base-200 hover:bg-error hover:text-white transition-all rounded-xl"
						onclick={() => product.id && onDelete(product.id)} 
						title="Eliminar"
					>
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-4 h-4">
							<path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
						</svg>
					</Button>
				</div>
			</div>

			{#if product.description}
				<p class="text-sm opacity-60 line-clamp-2 min-h-[2.5rem] leading-relaxed">
					{product.description}
				</p>
			{/if}
			
			<div class="flex items-center justify-between mt-auto pt-5 border-t border-base-100/50">
				<div class="flex flex-col">
					<span class="text-2xl font-black text-primary tracking-tight">
						${product.price.toFixed(2)}
					</span>
				</div>
				<div class="flex items-center gap-2">
					<span class="badge {product.is_active ? 'badge-success bg-success/20 text-success' : 'badge-ghost bg-base-200'} border-none font-black text-[10px] py-3 px-4 rounded-full">
						{product.is_active ? 'ACTIVO' : 'INACTIVO'}
					</span>
				</div>
			</div>
		</div>
	{/each}
</div>
