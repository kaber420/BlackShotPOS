<script lang="ts">
    import { ProductService, type Product } from '$lib/api/products';
    import { CategoryService, type Category } from '$lib/api/categories';
    import { onMount } from 'svelte';

    let products = $state<Product[]>([]);
    let categories = $state<Category[]>([]);
    let isLoading = $state(true);
    let error = $state('');
    let filterCategory = $state<number | null>(null);

    // Formulario reactivo
    let productForm = $state<Partial<Product>>({
        name: '',
        description: '',
        price: 0,
        image_url: '',
        category_id: undefined,
        is_active: true
    });

    let editingId = $state<number | null>(null);
    let isSubmitting = $state(false);

    async function loadData() {
        try {
            isLoading = true;
            const [p, c] = await Promise.all([
                ProductService.getAll(filterCategory || undefined, true),
                CategoryService.getAll()
            ]);
            products = p;
            categories = c;
        } catch (e: any) {
            error = e.message || 'Error al cargar productos';
        } finally {
            isLoading = false;
        }
    }

    async function handleFilterChange() {
        try {
            isLoading = true;
            products = await ProductService.getAll(filterCategory || undefined);
        } catch (e: any) {
            error = e.message;
        } finally {
            isLoading = false;
        }
    }

    function openModal(prod?: Product) {
        if (prod && prod.id) {
            editingId = prod.id;
            productForm = { ...prod };
        } else {
            editingId = null;
            productForm = {
                name: '',
                description: '',
                price: 0,
                image_url: '',
                category_id: categories.length > 0 ? categories[0].id : undefined,
                is_active: true
            };
        }
        (document.getElementById('modal_producto') as HTMLDialogElement).showModal();
    }

    async function handleSubmit(e: Event) {
        e.preventDefault();
        if (!productForm.name || productForm.price === undefined) return;

        try {
            isSubmitting = true;
            if (editingId) {
                const updated = await ProductService.update(editingId, productForm);
                products = products.map(p => p.id === editingId ? updated : p);
            } else {
                const created = await ProductService.create(productForm as Product);
                products = [...products, created];
            }
            (document.getElementById('modal_producto') as HTMLDialogElement)?.close();
        } catch (e: any) {
            alert('Error al guardar: ' + e.message);
        } finally {
            isSubmitting = false;
        }
    }

    async function handleDelete(id: number) {
        if (!confirm('¿Desactivar este producto? No aparecerá en el menú del POS.')) return;
        try {
            await ProductService.delete(id);
            products = products.map(p => p.id === id ? { ...p, is_active: false } : p);
        } catch (e: any) {
            alert('Error al desactivar: ' + e.message);
        }
    }

    onMount(() => {
        loadData();
    });
</script>

<div class="px-4 py-8 max-w-6xl mx-auto">
    <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
        <div>
            <h1 class="text-3xl font-bold text-base-content">Catálogo de Productos</h1>
            <p class="opacity-70 mt-1">Gestiona los productos que ofreces en tu menú.</p>
        </div>
        <div class="flex gap-2 w-full md:w-auto">
            <select class="select select-bordered" bind:value={filterCategory} onchange={handleFilterChange}>
                <option value={null}>Todas las categorías</option>
                {#each categories as cat}
                    <option value={cat.id}>{cat.name}</option>
                {/each}
            </select>
            <button class="btn btn-primary" onclick={() => openModal()}>
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                </svg>
                Nuevo Producto
            </button>
        </div>
    </div>

    {#if error}
        <div class="alert alert-error mb-4">
            <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            <span>{error}</span>
        </div>
    {/if}

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {#if isLoading}
            <div class="col-span-full flex flex-col items-center py-20">
                <span class="loading loading-spinner loading-lg text-primary"></span>
                <p class="mt-4 opacity-60">Cargando catálogo...</p>
            </div>
        {:else if products.length === 0}
            <div class="col-span-full text-center py-20 bg-base-200/30 rounded-2xl border-2 border-dashed border-base-300">
                <p class="opacity-60 italic text-lg">No hay productos en esta categoría.</p>
                <button class="btn btn-link no-underline" onclick={() => openModal()}>Crear el primero</button>
            </div>
        {:else}
            {#each products as prod}
                <div class="card bg-base-100 shadow-xl border border-base-200 group hover:border-primary/30 transition-all duration-300">
                    <figure class="px-4 pt-4 relative">
                        {#if prod.image_url}
                            <img src={prod.image_url} alt={prod.name} class="rounded-xl h-48 w-full object-cover bg-base-200" />
                        {:else}
                            <div class="h-48 w-full bg-base-200 rounded-xl flex items-center justify-center">
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 opacity-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                </svg>
                            </div>
                        {/if}
                        {#if !prod.is_active}
                            <div class="absolute inset-x-4 top-4 h-48 bg-base-300/80 rounded-xl flex items-center justify-center font-bold text-base-content/60">
                                DESACTIVADO
                            </div>
                        {/if}
                    </figure>
                    <div class="card-body">
                        <div class="flex justify-between items-start">
                            <h2 class="card-title text-xl">{prod.name}</h2>
                            <div class="badge badge-lg badge-secondary font-mono">${prod.price.toFixed(2)}</div>
                        </div>
                        <p class="text-sm opacity-70 line-clamp-2 min-h-[40px]">{prod.description || 'Sin descripción'}</p>
                        <div class="flex items-center gap-2 mt-2">
                            <div class="badge badge-outline text-xs">
                                {categories.find(c => c.id === prod.category_id)?.name || 'Sin Categoría'}
                            </div>
                        </div>
                        <div class="card-actions justify-end mt-4">
                            <button class="btn btn-ghost btn-sm" onclick={() => openModal(prod)}>
                                Editar
                            </button>
                            {#if prod.is_active}
                                <button class="btn btn-error btn-outline btn-sm" onclick={() => prod.id && handleDelete(prod.id)}>
                                    Desactivar
                                </button>
                            {/if}
                        </div>
                    </div>
                </div>
            {/each}
        {/if}
    </div>
</div>

<!-- Modal Producto (Crear / Editar) -->
<dialog id="modal_producto" class="modal">
    <div class="modal-box max-w-2xl">
        <h3 class="font-bold text-2xl mb-6">
            {editingId ? 'Editar Producto' : 'Nuevo Producto'}
        </h3>
        
        <form onsubmit={handleSubmit} class="space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <!-- Columna Izquierda -->
                <div class="space-y-4">
                    <div class="form-control w-full">
                        <label class="label" for="prod_name"><span class="label-text font-bold">Nombre</span></label>
                        <input id="prod_name" type="text" class="input input-bordered w-full" bind:value={productForm.name} required />
                    </div>

                    <div class="form-control w-full">
                        <label class="label" for="prod_cat"><span class="label-text font-bold">Categoría</span></label>
                        <select id="prod_cat" class="select select-bordered w-full" bind:value={productForm.category_id} required>
                            {#each categories as cat}
                                <option value={cat.id}>{cat.name}</option>
                            {/each}
                        </select>
                    </div>

                    <div class="form-control w-full">
                        <label class="label" for="prod_price"><span class="label-text font-bold text-secondary">Precio de Venta</span></label>
                        <div class="join">
                            <span class="btn join-item no-animation bg-base-200 border-base-300">$</span>
                            <input id="prod_price" type="number" step="0.01" class="input input-bordered w-full join-item" bind:value={productForm.price} required />
                        </div>
                    </div>
                </div>

                <!-- Columna Derecha -->
                <div class="space-y-4">
                    <div class="form-control w-full">
                        <label class="label" for="prod_img"><span class="label-text font-bold">URL de Imagen</span></label>
                        <input id="prod_img" type="text" class="input input-bordered w-full" bind:value={productForm.image_url} placeholder="https://..." />
                    </div>
                    
                    <div class="form-control w-full">
                        <label class="label" for="prod_active"><span class="label-text font-bold">Estado</span></label>
                        <label class="label cursor-pointer justify-start gap-4 bg-base-200 rounded-lg px-4">
                            <input id="prod_active" type="checkbox" class="toggle toggle-success" bind:checked={productForm.is_active} />
                            <span class="label-text font-medium">{productForm.is_active ? 'Activo' : 'Inactivo'}</span>
                        </label>
                    </div>
                </div>
            </div>

            <div class="form-control w-full">
                <label class="label" for="prod_desc"><span class="label-text font-bold">Descripción</span></label>
                <textarea id="prod_desc" class="textarea textarea-bordered h-24" bind:value={productForm.description} placeholder="Detalles del producto..."></textarea>
            </div>

            <div class="modal-action gap-2">
                <button type="button" class="btn btn-ghost" onclick={() => (document.getElementById('modal_producto') as HTMLDialogElement).close()}>
                    Cancelar
                </button>
                <button type="submit" class="btn btn-primary px-10" disabled={isSubmitting}>
                    {#if isSubmitting}
                        <span class="loading loading-spinner loading-sm"></span>
                    {/if}
                    {editingId ? 'Actualizar Producto' : 'Crear Producto'}
                </button>
            </div>
        </form>
    </div>
    <form method="dialog" class="modal-backdrop bg-black/60">
        <button>cerrar</button>
    </form>
</dialog>
