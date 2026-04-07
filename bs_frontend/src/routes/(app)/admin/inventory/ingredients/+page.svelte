<script lang="ts">
	import { IngredientService, type Ingredient } from '$lib/api/ingredients';
	import { ProductService, type ModifierGroup, type Modifier } from '$lib/api/products';
	import { onMount } from 'svelte';

	let ingredients = $state<Ingredient[]>([]);
	let modifierGroups = $state<ModifierGroup[]>([]);
	let isLoading = $state(true);
	let activeTab = $state<'ingredients' | 'groups'>('ingredients');
	let error = $state('');

	// Unidades de medida
	const UNIDADES = [
		{ id: 'kg', name: 'Kilogramos (kg)' },
		{ id: 'g', name: 'Gramos (g)' },
		{ id: 'l', name: 'Litros (L)' },
		{ id: 'ml', name: 'Mililitros (ml)' },
		{ id: 'oz', name: 'Onzas (oz)' },
		{ id: 'ud', name: 'Unidades/Piezas' },
		{ id: 'porcion', name: 'Porción' },
		{ id: 'taza', name: 'Tazas' }
	];

	// Formularios
	let ingredientForm = $state<Partial<Ingredient>>({ name: '', unit: 'g', current_stock: 0, minimum_stock: 0 });
	let groupForm = $state<Partial<ModifierGroup>>({ name: '', min_selection: 0, max_selection: 1, is_required: false });
	let modifierForm = $state<Partial<Modifier>>({ name: '', extra_price: 0, ingredient_id: undefined, quantity: 1 });

	let editingId = $state<number | null>(null);
	let selectedGroupId = $state<number | null>(null);
	let isSubmitting = $state(false);

	async function loadAllData() {
		try {
			isLoading = true;
			const [ings, groups] = await Promise.all([
				IngredientService.getAll(),
				ProductService.getModifierGroups()
			]);
			ingredients = ings;
			modifierGroups = groups;
		} catch (e: any) {
			error = e.message || 'Error al cargar datos';
		} finally {
			isLoading = false;
		}
	}

	async function handleDeleteIngredient(id: number) {
		if (!confirm('¿Eliminar este ingrediente de la base de datos?')) return;
		try {
			await IngredientService.delete(id);
			ingredients = ingredients.filter(i => i.id !== id);
		} catch (e: any) {
			alert('Error: ' + e.message);
		}
	}

	onMount(loadAllData);

	// --- Lógica de Ingredientes ---
	function openIngredientModal(ing?: Ingredient) {
		if (ing && ing.id) {
			editingId = ing.id;
			ingredientForm = { ...ing };
		} else {
			editingId = null;
			ingredientForm = { name: '', unit: 'g', current_stock: 0, minimum_stock: 0 };
		}
		(document.getElementById('modal_ingrediente') as HTMLDialogElement).showModal();
	}

	async function handleIngredientSubmit(e: Event) {
		e.preventDefault();
		try {
			isSubmitting = true;
			if (editingId) {
				const updated = await IngredientService.update(editingId, ingredientForm);
				ingredients = ingredients.map(i => i.id === editingId ? updated : i);
			} else {
				const created = await IngredientService.create(ingredientForm as Ingredient);
				ingredients = [...ingredients, created];
			}
			(document.getElementById('modal_ingrediente') as HTMLDialogElement)?.close();
		} catch (e: any) {
			alert('Error: ' + e.message);
		} finally {
			isSubmitting = false;
		}
	}

	// --- Lógica de Grupos de Opciones ---
	function openGroupModal(group?: ModifierGroup) {
		groupForm = group ? { ...group } : { name: '', min_selection: 0, max_selection: 1, is_required: false };
		(document.getElementById('modal_grupo') as HTMLDialogElement).showModal();
	}

	async function handleGroupSubmit(e: Event) {
		e.preventDefault();
		try {
			isSubmitting = true;
			const created = await ProductService.createModifierGroup(groupForm);
			modifierGroups = [...modifierGroups, created];
			(document.getElementById('modal_grupo') as HTMLDialogElement)?.close();
		} catch (e: any) {
			alert('Error: ' + e.message);
		} finally {
			isSubmitting = false;
		}
	}

	async function handleDeleteGroup(id: number) {
		if (!confirm('¿Eliminar este grupo y sus opciones?')) return;
		try {
			await ProductService.deleteModifierGroup(id);
			modifierGroups = modifierGroups.filter(g => g.id !== id);
		} catch (e: any) {
			alert('Error: ' + e.message);
		}
	}

	// --- Lógica de Modificadores (Opciones) ---
	function openModifierModal(groupId: number) {
		selectedGroupId = groupId;
		modifierForm = { name: '', extra_price: 0, ingredient_id: ingredients[0]?.id, quantity: 1 };
		(document.getElementById('modal_modificador') as HTMLDialogElement).showModal();
	}

	async function handleModifierSubmit(e: Event) {
		e.preventDefault();
		if (!selectedGroupId) return;
		try {
			isSubmitting = true;
			const created = await ProductService.createModifier({
				...modifierForm,
				modifier_group_id: selectedGroupId // Esta propiedad se añade en el backend o aquí
			} as any);
			
			// Recargar para ver los cambios vinculados
			await loadAllData();
			(document.getElementById('modal_modificador') as HTMLDialogElement)?.close();
		} catch (e: any) {
			alert('Error: ' + e.message);
		} finally {
			isSubmitting = false;
		}
	}

	async function handleDeleteModifier(id: number) {
		if (!confirm('¿Eliminar esta opción?')) return;
		try {
			await ProductService.deleteModifier(id);
			await loadAllData();
		} catch (e: any) {
			alert('Error: ' + e.message);
		}
	}
</script>

<div class="px-4 py-8 max-w-6xl mx-auto min-h-screen">
	<div class="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
		<div>
			<h1 class="text-4xl font-black text-base-content tracking-tighter">Inventario Maestros</h1>
			<p class="opacity-60 font-medium">Gestiona tu materia prima y grupos de personalización.</p>
		</div>
		
		<div class="tabs tabs-boxed bg-base-200 p-1 rounded-xl">
			<button class="tab tab-md transition-all duration-300 {activeTab === 'ingredients' ? 'tab-active bg-primary text-primary-content shadow-md' : ''}" onclick={() => activeTab = 'ingredients'}>
				Materiales
			</button>
			<button class="tab tab-md transition-all duration-300 {activeTab === 'groups' ? 'tab-active bg-secondary text-secondary-content shadow-md' : ''}" onclick={() => activeTab = 'groups'}>
				Grupos de Opciones
			</button>
		</div>
	</div>

	{#if activeTab === 'ingredients'}
		<!-- VISTA DE INGREDIENTES -->
		<div class="flex justify-between items-center mb-6">
			<h2 class="text-xl font-bold opacity-80 flex items-center gap-2">
				<div class="w-2 h-8 bg-primary rounded-full"></div>
				Insumos Base
			</h2>
			<button class="btn btn-primary shadow-lg shadow-primary/20" onclick={() => openIngredientModal()}>
				+ Insumo
			</button>
		</div>

		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
			{#if isLoading}
				{#each Array(6) as _}
					<div class="h-32 bg-base-300 animate-pulse rounded-2xl"></div>
				{/each}
			{:else}
				{#each ingredients as ing}
					<div class="bg-base-100 p-6 rounded-2xl border border-base-200 shadow-sm hover:shadow-md transition-all group overflow-hidden relative">
						<div class="flex justify-between items-start mb-4">
							<div>
								<h3 class="font-black text-lg truncate w-40">{ing.name}</h3>
								<span class="text-[10px] uppercase font-bold opacity-40">{ing.unit}</span>
							</div>
							<div class="flex gap-1">
								<button class="btn btn-square btn-ghost btn-xs" onclick={() => openIngredientModal(ing)} title="Editar">✎</button>
								<button class="btn btn-square btn-ghost btn-xs text-error" onclick={() => ing.id && handleDeleteIngredient(ing.id)} title="Eliminar">×</button>
							</div>
						</div>
						
						<div class="flex items-end justify-between">
							<div class="flex flex-col">
								<span class="text-2xl font-black {ing.current_stock <= ing.minimum_stock ? 'text-error' : 'text-primary'}">
									{ing.current_stock.toFixed(1)}
								</span>
								<span class="text-[9px] uppercase font-black opacity-30 tracking-widest leading-none">Disponible</span>
							</div>
							{#if ing.current_stock <= ing.minimum_stock}
								<div class="badge badge-error badge-xs font-bold animate-bounce">STOCK BAJO</div>
							{/if}
						</div>
					</div>
				{/each}
			{/if}
		</div>

	{:else}
		<!-- VISTA DE GRUPOS DE MODIFICADORES -->
		<div class="flex justify-between items-center mb-6">
			<h2 class="text-xl font-bold opacity-80 flex items-center gap-2">
				<div class="w-2 h-8 bg-secondary rounded-full"></div>
				Agrupaciones (Leches, Jarabes, etc.)
			</h2>
			<button class="btn btn-secondary shadow-lg shadow-secondary/20" onclick={() => openGroupModal()}>
				+ Nuevo Grupo
			</button>
		</div>

		<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
			{#each modifierGroups as group}
				<div class="bg-base-100 rounded-3xl border border-base-200 shadow-sm overflow-hidden flex flex-col">
					<div class="p-6 bg-base-200/50 border-b border-base-200 flex justify-between items-center">
						<div>
							<h3 class="font-black text-xl tracking-tight">{group.name}</h3>
							<p class="text-[10px] opacity-50 uppercase font-bold tracking-widest">
								{group.max_selection === 1 ? 'Selección Única' : `Máx ${group.max_selection} opciones`}
							</p>
						</div>
						<div class="flex gap-2">
							<button class="btn btn-circle btn-ghost btn-sm" onclick={() => openModifierModal(group.id!)}>+</button>
							<button class="btn btn-circle btn-ghost btn-sm text-error" onclick={() => handleDeleteGroup(group.id!)}>×</button>
						</div>
					</div>
					
					<div class="p-4 flex flex-col gap-2">
						{#if !group.modifiers || group.modifiers.length === 0}
							<p class="text-center py-8 text-xs italic opacity-40 uppercase font-bold">Sin opciones añadidas</p>
						{:else}
							<div class="grid grid-cols-1 gap-2">
								{#each group.modifiers as mod}
									<div class="flex items-center justify-between bg-base-100 p-4 rounded-2xl border border-base-200 group/item">
										<div class="flex items-center gap-4">
											<div class="w-10 h-10 bg-secondary/10 rounded-xl flex items-center justify-center text-secondary font-black">
												{mod.name[0]}
											</div>
											<div>
												<p class="font-bold text-sm leading-tight">{mod.name}</p>
												<p class="text-[10px] opacity-40">
													Vinculado: {ingredients.find(i => i.id === mod.ingredient_id)?.name || 'Sin vincular'}
												</p>
											</div>
										</div>
										<div class="flex items-center gap-4">
											<span class="text-xs font-black opacity-60">
												{mod.extra_price > 0 ? `+$${mod.extra_price}` : 'Incluido'}
											</span>
											<button class="btn btn-square btn-ghost btn-xs text-error opacity-0 group-hover/item:opacity-100" onclick={() => handleDeleteModifier(mod.id!)}>×</button>
										</div>
									</div>
								{/each}
							</div>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>

<!-- MODAL INGREDIENTE -->
<dialog id="modal_ingrediente" class="modal">
	<div class="modal-box rounded-3xl p-8">
		<h3 class="font-black text-2xl mb-6 tracking-tighter">Materia Prima</h3>
		<form onsubmit={handleIngredientSubmit} class="space-y-4">
			<div class="form-control">
				<label class="label p-0 mb-1" for="ing_name"><span class="label-text text-[10px] uppercase font-black opacity-40">Nombre</span></label>
				<input type="text" id="ing_name" bind:value={ingredientForm.name} class="input input-bordered focus:input-primary rounded-xl font-bold" required />
			</div>
			<div class="grid grid-cols-2 gap-4">
				<div class="form-control">
					<label class="label p-0 mb-1" for="ing_unit"><span class="label-text text-[10px] uppercase font-black opacity-40">Unidad</span></label>
					<select bind:value={ingredientForm.unit} class="select select-bordered rounded-xl font-bold">
						{#each UNIDADES as u}<option value={u.id}>{u.name}</option>{/each}
					</select>
				</div>
				<div class="form-control">
					<label class="label p-0 mb-1" for="ing_stock"><span class="label-text text-[10px] uppercase font-black opacity-40">Stock</span></label>
					<input type="number" step="0.1" bind:value={ingredientForm.current_stock} class="input input-bordered rounded-xl font-bold" />
				</div>
			</div>
			<div class="modal-action">
				<button type="submit" class="btn btn-primary rounded-xl px-10" disabled={isSubmitting}>Guardar</button>
			</div>
		</form>
	</div>
	<form method="dialog" class="modal-backdrop bg-black/40"><button>close</button></form>
</dialog>

<!-- MODAL GRUPO -->
<dialog id="modal_grupo" class="modal">
	<div class="modal-box rounded-3xl p-8">
		<h3 class="font-black text-2xl mb-6 tracking-tighter">Nuevo Grupo</h3>
		<form onsubmit={handleGroupSubmit} class="space-y-4">
			<div class="form-control">
				<label class="label p-0 mb-1" for="g_name"><span class="label-text text-[10px] uppercase font-black opacity-40">Nombre del Grupo (ej. Mis Leches)</span></label>
				<input type="text" id="g_name" bind:value={groupForm.name} class="input input-bordered focus:input-secondary rounded-xl font-bold" required />
			</div>
			<div class="modal-action">
				<button type="submit" class="btn btn-secondary rounded-xl px-10" disabled={isSubmitting}>Crear Grupo</button>
			</div>
		</form>
	</div>
	<form method="dialog" class="modal-backdrop bg-black/40"><button>close</button></form>
</dialog>

<!-- MODAL MODIFICADOR -->
<dialog id="modal_modificador" class="modal">
	<div class="modal-box rounded-3xl p-8">
		<h3 class="font-black text-2xl mb-6 tracking-tighter">Añadir Opción</h3>
		<form onsubmit={handleModifierSubmit} class="space-y-4">
			<div class="form-control">
				<label class="label p-0 mb-1" for="m_name"><span class="label-text text-[10px] uppercase font-black opacity-40">Nombre (ej. Leche Lala100)</span></label>
				<input type="text" id="m_name" bind:value={modifierForm.name} class="input input-bordered rounded-xl font-bold" required />
			</div>
			<div class="form-control">
				<label class="label p-0 mb-1" for="m_ing"><span class="label-text text-[10px] uppercase font-black opacity-40">Vincular al Inventario</span></label>
				<select bind:value={modifierForm.ingredient_id} class="select select-bordered rounded-xl font-bold">
					{#each ingredients as ing}<option value={ing.id}>{ing.name}</option>{/each}
				</select>
			</div>
			<div class="form-control">
				<label class="label p-0 mb-1" for="m_price"><span class="label-text text-[10px] uppercase font-black opacity-40">Precio Extra</span></label>
				<input type="number" bind:value={modifierForm.extra_price} class="input input-bordered rounded-xl font-bold" />
			</div>
			<div class="modal-action">
				<button type="submit" class="btn btn-secondary rounded-xl px-10" disabled={isSubmitting}>Guardar Opción</button>
			</div>
		</form>
	</div>
	<form method="dialog" class="modal-backdrop bg-black/40"><button>close</button></form>
</dialog>
