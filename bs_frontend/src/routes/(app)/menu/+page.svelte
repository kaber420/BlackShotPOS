<script lang="ts">
    import { onMount } from 'svelte';
    import { ProductService } from '$lib/api/products';
    import type { Product } from '$lib/api/products';
    import { CategoryService } from '$lib/api/categories';
    import type { Category } from '$lib/api/categories';
    import ProductModal from '$lib/components/ProductModal.svelte';
    import CategoryModal from '$lib/components/CategoryModal.svelte';
    import MeasureModal from '$lib/components/MeasureModal.svelte';
    import Button from '$lib/components/ui/Button.svelte';

    let products = $state<Product[]>([]);
    let categories = $state<Category[]>([]);
    let isLoading = $state(true);
    let searchQuery = $state('');
    let errorMessage = $state('');

    // Modal states
    let isProductModalOpen = $state(false);
    let isCategoryModalOpen = $state(false);
    let isMeasureModalOpen = $state(false);
    let editingProduct = $state<Partial<Product> | null>(null);

    const filteredProducts = $derived(
        products.filter(p => 
            p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            p.description?.toLowerCase().includes(searchQuery.toLowerCase())
        )
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
            categories = fetchedCategories;
        } catch (error) {
            console.error('Error loading menu data:', error);
            errorMessage = 'No se pudieron cargar los datos del menú.';
        } finally {
            isLoading = false;
        }
    }

    function getCategoryName(id?: number) {
        if (!id) return 'Sin categoría';
        return categories.find(c => c.id === id)?.name || 'Categoría desconocida';
    }

    function openCreateModal() {
        editingProduct = null;
        isProductModalOpen = true;
    }

    function openEditModal(product: Product) {
        editingProduct = { ...product };
        isProductModalOpen = true;
    }

    function openCategoryModal() {
        isCategoryModalOpen = true;
    }

    function openMeasureModal() {
        isMeasureModalOpen = true;
    }

    async function deleteProduct(id: number) {
        if (!confirm('¿Estás seguro de que deseas eliminar este producto?')) return;
        
        try {
            await ProductService.delete(id);
            await loadData();
        } catch (error) {
            console.error('Error deleting product:', error);
            errorMessage = 'No se pudo eliminar el producto.';
        }
    }

    onMount(loadData);
</script>

<div class="p-6 md:p-8 lg:p-12 max-w-7xl mx-auto flex flex-col gap-8">
    <header class="flex flex-col gap-2">
        <h1 class="text-4xl font-extrabold tracking-tight">Menú de Productos</h1>
        <p class="text-lg opacity-70">Administra los platillos y bebidas del establecimiento.</p>
    </header>

    <div class="flex flex-wrap gap-4 items-center justify-between">
        <div class="flex gap-2">
            <Button variant="primary" size="md" onclick={openCreateModal}>
                <svelte:fragment slot="icon">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
                </svelte:fragment>
                Nuevo Producto
            </Button>
            <Button variant="outline" size="md" onclick={openCategoryModal}>Categorías</Button>
            <Button variant="outline" size="md" onclick={openMeasureModal}>Tallas/Medidas</Button>
        </div>

        <div class="join">
            <input 
                class="input input-bordered join-item w-64 uppercase" 
                placeholder="Buscar producto..." 
                bind:value={searchQuery}
            />
            <Button variant="ghost" class="join-item bg-base-200" square>🔍</Button>
        </div>
    </div>

    {#if errorMessage}
        <div class="alert alert-error shadow-lg">
            <div>
                <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current flex-shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                <span>{errorMessage}</span>
            </div>
            <div class="flex-none">
                <Button variant="ghost" size="sm" onclick={loadData}>Reintentar</Button>
            </div>
        </div>
    {/if}

    <div class="hidden md:block overflow-x-auto bg-base-100 rounded-2xl shadow-sm border border-base-200">
        <table class="table table-lg">
            <thead class="bg-base-200/50">
                <tr>
                    <th class="font-bold">Producto</th>
                    <th class="font-bold">Categoría</th>
                    <th class="font-bold">Precio Base</th>
                    <th class="font-bold">Estado</th>
                    <th class="font-bold text-right">Acciones</th>
                </tr>
            </thead>
            <tbody>
                {#if isLoading}
                    {#each Array(3) as _}
                        <tr class="animate-pulse">
                            <td>
                                <div class="flex items-center gap-3">
                                    <div class="bg-base-300 rounded-full w-12 h-12"></div>
                                    <div class="h-4 bg-base-300 rounded w-32"></div>
                                </div>
                            </td>
                            <td><div class="h-4 bg-base-300 rounded w-16"></div></td>
                            <td><div class="h-4 bg-base-300 rounded w-12"></div></td>
                            <td><div class="h-4 bg-base-300 rounded w-20"></div></td>
                            <td class="text-right"><div class="h-8 bg-base-300 rounded w-16 ml-auto"></div></td>
                        </tr>
                    {/each}
                {:else if filteredProducts.length === 0}
                    <tr>
                        <td colspan="5" class="text-center py-12 opacity-50 italic">
                            {searchQuery ? 'No se encontraron productos que coincidan con la búsqueda.' : 'No hay productos registrados en el menú.'}
                        </td>
                    </tr>
                {:else}
                    {#each filteredProducts as product (product.id)}
                        <tr class="hover:bg-base-200/20 transition-colors">
                            <td>
                                <div class="flex items-center gap-3">
                                    <div class="avatar placeholder">
                                        <div class="bg-primary/10 text-primary rounded-full w-12 border border-primary/20">
                                            {#if product.image_url}
                                                <img src={product.image_url} alt={product.name} />
                                            {:else}
                                                <span class="text-xs font-bold">{product.name.substring(0, 2).toUpperCase()}</span>
                                            {/if}
                                        </div>
                                    </div>
                                    <div>
                                        <div class="font-bold text-lg">{product.name}</div>
                                        {#if product.description}
                                            <div class="text-sm opacity-50 max-w-xs truncate">{product.description}</div>
                                        {/if}
                                    </div>
                                </div>
                            </td>
                            <td><span class="badge badge-ghost border-base-300">{getCategoryName(product.category_id)}</span></td>
                            <td class="font-mono text-lg font-bold">${product.price.toFixed(2)}</td>
                            <td>
                                <span class="badge {product.is_active ? 'badge-success' : 'badge-ghost'} text-white font-bold p-3">
                                    {product.is_active ? 'Activo' : 'Inactivo'}
                                </span>
                            </td>
                            <td class="text-right">
                                <div class="flex justify-end gap-1">
                                    <Button variant="ghost" size="sm" class="text-primary" onclick={() => openEditModal(product)}>
                                        Editar
                                    </Button>
                                    <Button variant="ghost" size="sm" danger onclick={() => deleteProduct(product.id!)}>
                                        Eliminar
                                    </Button>
                                </div>
                            </td>
                        </tr>
                    {/each}
                {/if}
            </tbody>
        </table>
    </div>

    <!-- Mobile Card View -->
    <div class="grid grid-cols-1 gap-4 md:hidden">
        {#if isLoading}
            {#each Array(3) as _}
                <div class="bg-base-100 p-4 rounded-2xl border border-base-200 shadow-sm animate-pulse flex flex-col gap-4">
                    <div class="flex items-center gap-4">
                        <div class="bg-base-300 rounded-full w-14 h-14 shrink-0"></div>
                        <div class="flex-1 space-y-2">
                            <div class="h-4 bg-base-300 rounded w-3/4"></div>
                            <div class="h-3 bg-base-300 rounded w-1/2"></div>
                        </div>
                    </div>
                    <div class="flex justify-between items-center">
                        <div class="h-6 bg-base-300 rounded w-1/4"></div>
                        <div class="h-8 bg-base-300 rounded w-1/3"></div>
                    </div>
                </div>
            {/each}
        {:else if filteredProducts.length === 0}
            <div class="text-center py-8 opacity-50 italic bg-base-100 rounded-2xl border border-base-200 shadow-sm">
                {searchQuery ? 'No se encontraron productos que coincidan con la búsqueda.' : 'No hay productos registrados en el menú.'}
            </div>
        {:else}
            {#each filteredProducts as product (product.id)}
                <div class="bg-base-100 p-4 rounded-2xl border border-base-200 shadow-sm flex flex-col gap-4 hover:shadow-md transition-shadow">
                    <div class="flex justify-between items-start gap-4">
                        <div class="flex items-center gap-3">
                            <div class="avatar placeholder shrink-0">
                                <div class="bg-primary/10 text-primary rounded-full w-14 border border-primary/20">
                                    {#if product.image_url}
                                        <img src={product.image_url} alt={product.name} class="object-cover" />
                                    {:else}
                                        <span class="text-sm font-bold">{product.name.substring(0, 2).toUpperCase()}</span>
                                    {/if}
                                </div>
                            </div>
                            <div>
                                <div class="font-bold text-lg leading-tight">{product.name}</div>
                                <div class="text-sm opacity-60 mt-0.5">{getCategoryName(product.category_id)}</div>
                            </div>
                        </div>
                        <span class="badge {product.is_active ? 'badge-success' : 'badge-ghost'} text-white font-bold p-2.5 text-xs">
                            {product.is_active ? 'Activo' : 'Inactivo'}
                        </span>
                    </div>
                    
                    {#if product.description}
                        <p class="text-sm opacity-70 line-clamp-2">{product.description}</p>
                    {/if}
                    
                    <div class="flex justify-between items-center mt-2 pt-3 border-t border-base-200">
                        <div class="font-mono text-xl font-bold">${product.price.toFixed(2)}</div>
                        <div class="flex gap-2">
                            <Button variant="ghost" size="sm" class="text-primary" onclick={() => openEditModal(product)}>
                                Editar
                            </Button>
                            <Button variant="ghost" size="sm" danger onclick={() => deleteProduct(product.id!)}>
                                Eliminar
                            </Button>
                        </div>
                    </div>
                </div>
            {/each}
        {/if}
    </div>
</div>

<ProductModal 
    isOpen={isProductModalOpen} 
    product={editingProduct} 
    {categories}
    onClose={() => isProductModalOpen = false} 
    onSave={loadData} 
/>

<CategoryModal 
    isOpen={isCategoryModalOpen} 
    onClose={() => isCategoryModalOpen = false} 
    onRefresh={loadData} 
/>

<MeasureModal
    isOpen={isMeasureModalOpen}
    onClose={() => isMeasureModalOpen = false}
    onRefresh={loadData}
/>
