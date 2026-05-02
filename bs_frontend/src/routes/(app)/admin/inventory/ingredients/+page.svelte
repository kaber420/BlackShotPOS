<script lang="ts">
	import { IngredientService, type Ingredient, type InventoryAdjustmentCreate, AdjustmentReason } from '$lib/api/ingredients';
	import { can } from '$lib/app_state.svelte';
	import { ProductService, type ModifierGroup, type Modifier } from '$lib/api/products';
	import { onMount } from 'svelte';
    import Button from '$lib/components/ui/Button.svelte';
	import { posSocket } from '$lib/pos_socket.svelte';

	let ingredients = $state<Ingredient[]>([]);
	let modifierGroups = $state<ModifierGroup[]>([]);
	let isLoading = $state(true);
	let activeTab = $state<'ingredients' | 'groups'>('ingredients');
	let error = $state('');

	// Unidades de medida restringidas por tipo
	const UNIT_OPTIONS = {
		weight: [
			{ id: 'g', name: 'Gramos (g)' },
			{ id: 'kg', name: 'Kilogramos (kg)' },
			{ id: 'oz', name: 'Onzas (oz)' },
			{ id: 'lb', name: 'Libras (lb)' }
		],
		volume: [
			{ id: 'ml', name: 'Mililitros (ml)' },
			{ id: 'L', name: 'Litros (L)' },
			{ id: 'fl_oz', name: 'Onzas Líquidas (fl oz)' }
		],
		unit: [
			{ id: 'pz', name: 'Piezas (pz)' },
			{ id: 'ud', name: 'Unidades' },
			{ id: 'porcion', name: 'Porción' }
		]
	};

	const MEASURE_TYPES = [
		{ id: 'weight', name: 'Sólido / Peso', icon: '⚖️' },
		{ id: 'volume', name: 'Líquido / Volumen', icon: '💧' },
		{ id: 'unit', name: 'Pieza / Unidad', icon: '📦' }
	];

	// Formularios
	let ingredientForm = $state<Partial<Ingredient>>({ 
		name: '', 
		measure_type: 'weight', 
		unit: 'g', 
		current_stock: 0, 
		minimum_stock: 0 
	});
	let groupForm = $state<Partial<ModifierGroup>>({ name: '', min_selection: 0, max_selection: 1, is_required: false });
	let modifierForm = $state<Partial<Modifier>>({ 
		name: '', 
		extra_price: 0, 
		ingredient_id: undefined, 
		input_quantity: 0, 
		input_unit: 'ml' 
	});

	let editingId = $state<number | null>(null);
	let selectedGroupId = $state<number | null>(null);
	let isSubmitting = $state(false);
	let showAdvancedModifier = $state(false);

	// --- Lógica de Merma ---
	let adjustmentForm = $state<InventoryAdjustmentCreate>({
		ingredient_id: 0,
		quantity: 0,
		reason: AdjustmentReason.WASTE,
		note: ''
	});
	let selectedIngredientForAdjustment = $state<Ingredient | null>(null);

	const REASON_LABELS = {
		[AdjustmentReason.WASTE]: 'Desperdicio',
		[AdjustmentReason.EXPIRED]: 'Caducado',
		[AdjustmentReason.ERROR]: 'Error de Prep',
		[AdjustmentReason.THEFT]: 'Robo',
		[AdjustmentReason.PERSONAL_CONSUMPTION]: 'Consumo Personal',
		[AdjustmentReason.PURCHASE]: 'Compra',
		[AdjustmentReason.RESTOCK]: 'Reposición',
		[AdjustmentReason.PHYSICAL_COUNT]: 'Conteo Físico',
		[AdjustmentReason.CORRECTION]: 'Corrección'
	};

	let movementType = $state<'IN' | 'OUT' | 'SET'>('OUT');

	function openAdjustmentModal(ing: Ingredient, type: 'IN' | 'OUT' | 'SET' = 'OUT') {
		selectedIngredientForAdjustment = ing;
		movementType = type;
		
		let defaultReason = AdjustmentReason.WASTE;
		if (type === 'IN') defaultReason = AdjustmentReason.PURCHASE;
		if (type === 'SET') defaultReason = AdjustmentReason.PHYSICAL_COUNT;

		adjustmentForm = {
			ingredient_id: ing.id!,
			quantity: 0,
			reason: defaultReason,
			note: '',
			expiration_date: ''
		};
		(document.getElementById('modal_merma') as HTMLDialogElement).showModal();
	}

	// Reactividad para resetear el motivo al cambiar de pestaña
	$effect(() => {
		if (movementType === 'IN') adjustmentForm.reason = AdjustmentReason.PURCHASE;
		else if (movementType === 'SET') adjustmentForm.reason = AdjustmentReason.PHYSICAL_COUNT;
		else if (movementType === 'OUT') adjustmentForm.reason = AdjustmentReason.WASTE;
	});

	async function handleAdjustmentSubmit(e: Event) {
		e.preventDefault();
		try {
			isSubmitting = true;
			await IngredientService.registerAdjustment(adjustmentForm);
			(document.getElementById('modal_merma') as HTMLDialogElement)?.close();
		} catch (e: any) {
			alert('Error al registrar merma: ' + e.message);
		} finally {
			isSubmitting = false;
		}
	}

	async function loadAllData() {
		try {
			isLoading = true;
			error = '';
			
			// Cargamos en paralelo para máxima velocidad
			const [ings, groups] = await Promise.all([
				IngredientService.getAll(),
				ProductService.getModifierGroups()
			]);
			
			ingredients = ings;
			modifierGroups = groups;
		} catch (e: any) {
			console.error('Error cargando datos maestros:', e);
			error = 'Error al cargar datos maestros: ' + (e.message || 'Error desconocido');
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

	onMount(() => {
		loadAllData();
		posSocket.subscribe('inventory');
	});

	$effect(() => {
		if (posSocket.ingredients.length > 0) {
			ingredients = posSocket.ingredients;
		}
	});

	// --- Lógica de Ingredientes ---
	function openIngredientModal(ing?: Ingredient) {
		if (ing && ing.id) {
			editingId = ing.id;
			ingredientForm = { ...ing };
		} else {
			editingId = null;
			ingredientForm = { name: '', measure_type: 'weight', unit: 'g', current_stock: 0, minimum_stock: 0 };
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
		showAdvancedModifier = false;
		const firstIng = ingredients[0];
		modifierForm = { 
			name: '', 
			extra_price: 0, 
			ingredient_id: firstIng?.id, 
			input_quantity: 0, 
			input_unit: firstIng ? UNIT_OPTIONS[firstIng.measure_type][0].id : 'ml' 
		};
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

<div class="px-4 py-8 max-w-6xl mx-auto flex-1 min-h-0 overflow-y-auto w-full w-full">
	<div class="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
		<div>
			<h1 class="text-4xl font-black text-base-content tracking-tighter">Inventario Maestros</h1>
			<p class="opacity-60 font-medium">Gestiona tu materia prima y grupos de personalización.</p>
		</div>
    
    {#if error}
        <div class="alert alert-error mb-6 rounded-2xl shadow-lg border-none bg-error/20 text-error-content font-bold">
            <span class="text-xl">⚠️</span>
            <span>{error}</span>
            <button class="btn btn-sm btn-ghost" onclick={loadAllData}>Reintentar</button>
        </div>
    {/if}
		
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
			<Button variant="primary" onclick={() => openIngredientModal()}>
				+ Insumo
			</Button>
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
								<div class="flex items-center gap-1">
									<span class="text-[10px] uppercase font-bold opacity-40">{ing.unit}</span>
									<span class="text-[10px] opacity-40">•</span>
									<span class="text-[10px] uppercase font-bold opacity-40">
										{MEASURE_TYPES.find(t => t.id === ing.measure_type)?.icon} {ing.measure_type}
									</span>
								</div>
							</div>
							<div class="flex gap-1">
								{#if can.manageInventory()}
									<Button variant="ghost" square size="xs" onclick={() => openAdjustmentModal(ing)} title="Movimientos" class="text-warning">📊</Button>
								{/if}
								<Button variant="ghost" square size="xs" onclick={() => openIngredientModal(ing)} title="Editar">✎</Button>
								<Button variant="ghost" square size="xs" danger onclick={() => ing.id && handleDeleteIngredient(ing.id)} title="Eliminar">×</Button>
							</div>
						</div>
						
						<div class="flex items-end justify-between">
							<div class="flex flex-col">
								<span class="text-2xl font-black {ing.current_stock <= ing.minimum_stock ? 'text-error' : 'text-primary'}">
									{ing.current_stock.toFixed(1)} <small class="text-[10px] font-bold opacity-50">{ing.unit}</small>
								</span>
								<span class="text-[9px] uppercase font-black opacity-30 tracking-widest leading-none">Disponible</span>
							</div>
							<div class="flex flex-col items-end gap-1">
								{#if ing.current_stock <= ing.minimum_stock}
									<div class="badge badge-error badge-xs font-bold animate-bounce text-[8px] p-2">STOCK BAJO</div>
								{/if}
								
								{#if ing.batches && ing.batches.some(b => b.expiration_date && new Date(b.expiration_date).getTime() < (new Date().getTime() + 3*24*60*60*1000))}
									<div class="badge badge-warning badge-xs font-black text-[8px] p-2">CADUCIDAD CERCANA</div>
								{/if}
							</div>
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
			<Button variant="secondary" onclick={() => openGroupModal()}>
				+ Nuevo Grupo
			</Button>
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
							<Button variant="ghost" circle size="sm" onclick={() => openModifierModal(group.id!)}>+</Button>
							<Button variant="ghost" circle size="sm" danger onclick={() => handleDeleteGroup(group.id!)}>×</Button>
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
											<Button variant="ghost" square size="xs" danger class="opacity-0 group-hover/item:opacity-100" onclick={() => handleDeleteModifier(mod.id!)}>×</Button>
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
			<div class="form-control">
				<label class="label p-0 mb-1"><span class="label-text text-[10px] uppercase font-black opacity-40">Naturaleza del Insumo</span></label>
				<div class="grid grid-cols-3 gap-2">
					{#each MEASURE_TYPES as type}
						<button 
							type="button"
							class="flex flex-col items-center p-3 rounded-2xl border-2 transition-all {ingredientForm.measure_type === type.id ? 'border-primary bg-primary/5' : 'border-base-200'}"
							onclick={() => {
								ingredientForm.measure_type = type.id as any;
								ingredientForm.unit = UNIT_OPTIONS[type.id as keyof typeof UNIT_OPTIONS][0].id;
							}}
						>
							<span class="text-xl">{type.icon}</span>
							<span class="text-[8px] font-black uppercase mt-1">{type.name}</span>
						</button>
					{/each}
				</div>
			</div>

			<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
				<div class="form-control">
					<label class="label p-0 mb-1" for="ing_unit"><span class="label-text text-[10px] uppercase font-black opacity-40">Unidad Base</span></label>
					<select bind:value={ingredientForm.unit} class="select select-bordered rounded-xl font-bold">
						{#each UNIT_OPTIONS[ingredientForm.measure_type as keyof typeof UNIT_OPTIONS] || [] as u}
							<option value={u.id}>{u.name}</option>
						{/each}
					</select>
				</div>
				<div class="form-control">
					<label class="label p-0 mb-1" for="ing_stock">
                        <span class="label-text text-[10px] uppercase font-black opacity-40">Stock Actual ({ingredientForm.unit})</span>
                    </label>
					<input type="number" step="0.1" bind:value={ingredientForm.current_stock} class="input input-bordered rounded-xl font-bold bg-base-200" readonly title="El stock se ajusta mediante Movimientos" />
				</div>
				<div class="form-control">
					<label class="label p-0 mb-1" for="ing_min_stock">
                        <span class="label-text text-[10px] uppercase font-black opacity-40">Stock Mínimo</span>
                    </label>
					<input type="number" step="0.1" id="ing_min_stock" bind:value={ingredientForm.minimum_stock} class="input input-bordered rounded-xl font-bold border-warning/30" />
				</div>
			</div>
			<div class="modal-action">
				<Button type="submit" variant="primary" class="px-10" isLoading={isSubmitting}>Guardar</Button>
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
				<Button type="submit" variant="secondary" class="px-10" isLoading={isSubmitting}>Crear Grupo</Button>
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
				<label class="label p-0 mb-1" for="m_name"><span class="label-text text-[10px] uppercase font-black opacity-40">Nombre de la Opción (ej. Soya)</span></label>
				<input type="text" id="m_name" bind:value={modifierForm.name} class="input input-bordered rounded-xl font-bold" required />
			</div>
			<div class="form-control">
				<label class="label p-0 mb-1" for="m_ing"><span class="label-text text-[10px] uppercase font-black opacity-40">Vincular al Inventario (Insumo)</span></label>
				<select 
					bind:value={modifierForm.ingredient_id} 
					class="select select-bordered rounded-xl font-bold"
					onchange={() => {
						const ing = ingredients.find(i => i.id === modifierForm.ingredient_id);
						if (ing) modifierForm.input_unit = ing.unit;
					}}
				>
					<option value={undefined}>No descontar inventario</option>
					{#each ingredients as ing}<option value={ing.id}>{ing.name}</option>{/each}
				</select>
			</div>

			<div class="form-control">
				<label class="label p-0 mb-1" for="m_price"><span class="label-text text-[10px] uppercase font-black opacity-40">Precio Extra ($)</span></label>
				<input type="number" bind:value={modifierForm.extra_price} class="input input-bordered rounded-xl font-bold" />
			</div>

			<div class="py-2">
				<button 
					type="button" 
					class="text-[10px] uppercase font-black opacity-40 hover:opacity-100 flex items-center gap-1 transition-all"
					onclick={() => showAdvancedModifier = !showAdvancedModifier}
				>
					{showAdvancedModifier ? '▾ Ocultar' : '▸'} Configuración de Descuento Fijo (Opcional)
				</button>
				
				{#if showAdvancedModifier}
					<div class="grid grid-cols-2 gap-4 mt-3 p-4 bg-base-200/50 rounded-2xl animate-in fade-in slide-in-from-top-2">
						<div class="form-control">
							<label class="label p-0 mb-1" for="m_qty"><span class="label-text text-[9px] uppercase font-bold opacity-60">Cantidad Fija</span></label>
							<input type="number" step="0.01" bind:value={modifierForm.input_quantity} class="input input-bordered input-sm rounded-xl font-bold" />
						</div>
						<div class="form-control">
							<label class="label p-0 mb-1" for="m_unit"><span class="label-text text-[9px] uppercase font-bold opacity-60">Unidad</span></label>
							<select 
								bind:value={modifierForm.input_unit} 
								class="select select-bordered select-sm rounded-xl font-bold"
							>
								{#if ingredients.find(i => i.id === modifierForm.ingredient_id)}
									{#each UNIT_OPTIONS[ingredients.find(i => i.id === modifierForm.ingredient_id)!.measure_type] as u}
										<option value={u.id}>{u.name}</option>
									{/each}
								{:else}
									<option value="ml">ml</option>
								{/if}
							</select>
						</div>
						<p class="col-span-2 text-[9px] opacity-50 italic">
							* Usa esto solo si la cantidad es SIEMPRE la misma. Si depende de la receta (Chico/Grande), déjalo en 0.
						</p>
					</div>
				{/if}
			</div>

			<div class="modal-action">
				<Button type="submit" variant="secondary" class="px-10" isLoading={isSubmitting}>Guardar Opción</Button>
			</div>
		</form>
	</div>
	<form method="dialog" class="modal-backdrop bg-black/40"><button>close</button></form>
</dialog>

<!-- MODAL MOVIMIENTOS / AJUSTE -->
<dialog id="modal_merma" class="modal">
	<div 
		class="modal-box rounded-[2rem] p-8 transition-all duration-500 bg-base-100 border border-white/5"
		style="box-shadow: 0 0 50px -10px {movementType === 'IN' ? 'rgba(34, 197, 94, 0.3)' : movementType === 'SET' ? 'rgba(59, 130, 246, 0.3)' : 'rgba(239, 68, 68, 0.3)'}"
	>
		<div class="flex justify-between items-start mb-8">
			<div>
				<h3 class="font-black text-4xl tracking-tighter bg-clip-text text-transparent bg-gradient-to-r {movementType === 'IN' ? 'from-success to-emerald-400' : movementType === 'SET' ? 'from-primary to-blue-400' : 'from-error to-rose-400'}">
					Movimiento
				</h3>
				<p class="text-[10px] opacity-40 uppercase font-black tracking-[0.2em] mt-1">{selectedIngredientForAdjustment?.name}</p>
			</div>
			<form method="dialog">
				<button class="btn btn-sm btn-circle btn-ghost opacity-30 hover:opacity-100 transition-all">✕</button>
			</form>
		</div>

		<!-- Selector de Tipo (Pestañas Neon) -->
		<div class="flex p-1.5 bg-base-200/50 rounded-2xl mb-10 gap-1 border border-white/5">
			<button 
				type="button" 
				class="flex-1 py-3 rounded-xl text-xs font-black uppercase tracking-wider transition-all duration-300 {movementType === 'IN' ? 'bg-success text-success-content shadow-[0_0_15px_rgba(34,197,94,0.4)] scale-100' : 'opacity-40 hover:opacity-70 scale-95'}" 
				onclick={() => movementType = 'IN'}
			>
				📥 Entrada
			</button>
			<button 
				type="button" 
				class="flex-1 py-3 rounded-xl text-xs font-black uppercase tracking-wider transition-all duration-300 {movementType === 'OUT' ? 'bg-error text-error-content shadow-[0_0_15px_rgba(239,68,68,0.4)] scale-100' : 'opacity-40 hover:opacity-70 scale-95'}" 
				onclick={() => movementType = 'OUT'}
			>
				📤 Salida
			</button>
			<button 
				type="button" 
				class="flex-1 py-3 rounded-xl text-xs font-black uppercase tracking-wider transition-all duration-300 {movementType === 'SET' ? 'tab-active bg-primary text-primary-content shadow-[0_0_15px_rgba(59,130,246,0.4)] scale-100' : 'opacity-40 hover:opacity-70 scale-95'}" 
				onclick={() => movementType = 'SET'}
			>
				⚖️ Conteo
			</button>
		</div>
		
		<form onsubmit={handleAdjustmentSubmit} class="space-y-8">
			<div class="grid grid-cols-1 md:grid-cols-2 gap-8">
				<div class="form-control">
					<label class="label p-0 mb-3" for="adj_qty">
						<span class="label-text text-[10px] uppercase font-black opacity-30 tracking-widest">
							{#if movementType === 'SET'}Cantidad Real
							{:else}Cantidad a {#if movementType === 'IN'}Ingresar{:else}Descontar{/if}{/if} ({selectedIngredientForAdjustment?.unit})
						</span>
					</label>
					<input 
						type="number" 
						step="0.01" 
						id="adj_qty" 
						bind:value={adjustmentForm.quantity} 
						class="input input-lg bg-base-200/50 border-none rounded-[1.5rem] font-black text-3xl h-20 focus:ring-2 {movementType === 'IN' ? 'focus:ring-success/30' : movementType === 'SET' ? 'focus:ring-primary/30' : 'focus:ring-error/30'} transition-all" 
						placeholder="0.00" 
						required 
					/>
				</div>
				<div class="form-control">
					<label class="label p-0 mb-3" for="adj_reason">
						<span class="label-text text-[10px] uppercase font-black opacity-30 tracking-widest">Razón</span>
					</label>
					<select bind:value={adjustmentForm.reason} class="select select-lg bg-base-200/50 border-none rounded-[1.5rem] font-bold h-20 text-lg transition-all">
						{#each Object.entries(REASON_LABELS) as [value, label]}
							{#if movementType === 'IN' && (value === 'PURCHASE' || value === 'RESTOCK')}
								<option {value}>{label}</option>
							{:else if movementType === 'OUT' && ['WASTE', 'EXPIRED', 'ERROR', 'THEFT', 'PERSONAL_CONSUMPTION'].includes(value)}
								<option {value}>{label}</option>
							{:else if movementType === 'SET' && (value === 'PHYSICAL_COUNT' || value === 'CORRECTION')}
								<option {value}>{label}</option>
							{/if}
						{/each}
					</select>
				</div>
			</div>

			{#if movementType === 'IN'}
				<div class="form-control animate-in fade-in slide-in-from-top-2">
					<label class="label p-0 mb-3" for="adj_expiry">
						<span class="label-text text-[10px] uppercase font-black opacity-30 tracking-widest">Fecha de Caducidad (Opcional)</span>
					</label>
					<input 
						type="date" 
						id="adj_expiry" 
						bind:value={adjustmentForm.expiration_date} 
						class="input input-lg bg-base-200/50 border-none rounded-[1.5rem] font-bold h-20 text-lg transition-all"
					/>
				</div>
			{/if}

			{#if movementType === 'SET'}
				<div class="flex gap-4 p-5 rounded-2xl bg-primary/5 border border-primary/10 items-center">
					<div class="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center text-xl shadow-[0_0_15px_rgba(59,130,246,0.3)]">💡</div>
					<p class="text-[11px] font-medium leading-relaxed opacity-70">
						El stock actual (<span class="font-black text-primary">{selectedIngredientForAdjustment?.current_stock}</span>) será reemplazado por el valor ingresado.
					</p>
				</div>
			{/if}

			<div class="form-control">
				<label class="label p-0 mb-3" for="adj_note">
					<span class="label-text text-[10px] uppercase font-black opacity-30 tracking-widest">Notas de Auditoría</span>
				</label>
				<textarea 
					id="adj_note" 
					bind:value={adjustmentForm.note} 
					class="textarea bg-base-200/50 border-none rounded-2xl font-medium h-24 text-sm focus:ring-1 focus:ring-white/10" 
					placeholder="Ej: Factura #123, Lote caducado, ajuste semanal..."
				></textarea>
			</div>

			<div class="modal-action mt-4">
				<Button 
					type="submit" 
					variant="primary" 
					class="btn-lg btn-block rounded-2xl border-none font-black uppercase tracking-[0.2em] shadow-2xl transition-all duration-300 hover:scale-[1.01] active:scale-[0.98] {movementType === 'IN' ? 'bg-success text-success-content shadow-success/20' : movementType === 'SET' ? 'bg-primary text-primary-content shadow-primary/20' : 'bg-error text-error-content shadow-error/20'}" 
					isLoading={isSubmitting}
				>
					Confirmar Registro
				</Button>
			</div>
		</form>
	</div>
	<form method="dialog" class="modal-backdrop bg-black/80 backdrop-blur-md"><button>close</button></form>
</dialog>
