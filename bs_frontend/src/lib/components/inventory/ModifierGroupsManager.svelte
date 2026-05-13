<script lang="ts">
    import { ProductService, type ModifierGroup } from '$lib/api/products';
    import { IngredientService, type Ingredient } from '$lib/api/ingredients';
    import Button from '$lib/components/ui/Button.svelte';
    import ModifierGroupModal from './ModifierGroupModal.svelte';
    import ModifierModal from './ModifierModal.svelte';
    import { untrack } from 'svelte';

    type Props = { isOpen: boolean, onClose: () => void };
    let { isOpen, onClose } = $props<Props>();

    let modifierGroups = $state<ModifierGroup[]>([]);
    let ingredients = $state<Ingredient[]>([]);
    let isLoading = $state(false);
    let groupSearch = $state('');

    // Modal state for internal actions
    let isGroupModalOpen = $state(false);
    let isModifierModalOpen = $state(false);
    let editingGroup = $state<ModifierGroup | null>(null);
    let selectedGroupId = $state<number | null>(null);

    const filteredGroups = $derived(
        modifierGroups.filter(g => g.name.toLowerCase().includes(groupSearch.toLowerCase()))
    );

    async function loadData() {
        isLoading = true;
        try {
            const [groups, ings] = await Promise.all([
                ProductService.getModifierGroups(),
                IngredientService.getAll()
            ]);
            modifierGroups = groups;
            ingredients = ings;
        } catch (e) {
            console.error("Error loading modifier groups data", e);
        } finally {
            isLoading = false;
        }
    }

    let isDeleting = $state(false);

    $effect(() => {
        if (isOpen && !isDeleting) {
            untrack(() => loadData());
        }
    });

    async function handleDeleteGroup(id: number) {
        console.log("CRITICAL: Calling handleDeleteGroup with ID:", id);
        if (!window.confirm('¿ELIMINAR GRUPO?')) return;
        
        isDeleting = true;
        try {
            const result = await ProductService.deleteModifierGroup(id);
            console.log("Delete result:", result);
            await loadData();
            alert('Grupo eliminado con éxito');
        } catch (e: any) {
            console.error("FAIL:", e);
            alert('ERROR CRITICO: ' + (e.message || 'Error desconocido'));
        } finally {
            isDeleting = false;
        }
    }

    async function handleDeleteModifier(id: number) {
        if (!confirm('¿Eliminar esta opción?')) return;
        try {
            await ProductService.deleteModifier(id);
            await loadData();
        } catch (e: any) {
            alert('Error: ' + e.message);
        }
    }
</script>

{#if isOpen}
    <div class="modal modal-open bg-base-300/80 backdrop-blur-md z-[60]">
        <div class="modal-box w-11/12 max-w-6xl h-[90vh] flex flex-col p-0 overflow-hidden rounded-[2.5rem] shadow-2xl border border-base-content/5">
            <!-- Header -->
            <div class="p-8 bg-base-100 border-b border-base-200 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 shrink-0">
                <div class="flex items-center gap-4">
                    <div class="w-12 h-12 bg-secondary/10 rounded-2xl flex items-center justify-center text-secondary">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16m-7 6h7" /></svg>
                    </div>
                    <div>
                        <h2 class="text-3xl font-black tracking-tighter uppercase">
                            Gestión de Grupos
                        </h2>
                        <p class="text-[10px] opacity-40 font-black uppercase tracking-widest mt-0.5">Control de modificadores y complementos</p>
                    </div>
                </div>

                <div class="flex flex-1 max-w-md w-full relative">
                    <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 opacity-20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                    </div>
                    <input 
                        type="text" 
                        bind:value={groupSearch}
                        placeholder="Buscar grupos..." 
                        class="input input-bordered w-full pl-10 rounded-2xl bg-base-200/50 focus:bg-base-100 transition-all font-bold text-sm"
                    />
                </div>

                <div class="flex gap-3">
                    <Button variant="secondary" class="rounded-2xl font-black px-6 shadow-lg shadow-secondary/20" onclick={() => { editingGroup = null; isGroupModalOpen = true; }}>
                        + Nuevo Grupo
                    </Button>
                    <Button variant="ghost" circle onclick={onClose} class="hover:bg-error/10 hover:text-error transition-all">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
                    </Button>
                </div>
            </div>

            <!-- Content -->
            <div class="flex-1 overflow-y-auto p-6 bg-base-200/30">
                {#if isLoading && modifierGroups.length === 0}
                    <div class="flex flex-col items-center justify-center py-20 gap-4">
                        <span class="loading loading-ring loading-lg text-secondary"></span>
                        <span class="text-xs font-black opacity-40 uppercase tracking-widest">Cargando grupos...</span>
                    </div>
                {:else if filteredGroups.length === 0}
                    <div class="flex flex-col items-center justify-center py-20 bg-base-100 rounded-3xl border-2 border-dashed border-base-300">
                        <span class="text-4xl mb-4">🔍</span>
                        <p class="text-sm font-bold opacity-40 uppercase tracking-widest">No se encontraron resultados</p>
                        <Button variant="ghost" class="mt-4" onclick={() => groupSearch = ''}>Limpiar búsqueda</Button>
                    </div>
                {:else}
                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {#each filteredGroups as group}
                            <div class="bg-base-100 rounded-3xl border border-base-200 shadow-sm flex flex-col overflow-hidden group/card hover:shadow-xl transition-all">
                                <div class="p-6 border-b border-base-200 flex justify-between items-center bg-base-50/50">
                                    <div class="space-y-1">
                                        <h4 class="font-black text-xl tracking-tight uppercase">{group.name}</h4>
                                        <div class="flex gap-2">
                                            <span class="badge badge-sm font-bold {group.is_required ? 'badge-secondary' : 'badge-ghost'}">
                                                {group.is_required ? 'Obligatorio' : 'Opcional'}
                                            </span>
                                            <span class="badge badge-sm badge-ghost font-bold">
                                                Min: {group.min_selection} / Max: {group.max_selection}
                                            </span>
                                        </div>
                                    </div>
                                    <div class="flex gap-1">
                                        <Button 
                                            variant="ghost" 
                                            circle 
                                            size="sm" 
                                            class="hover:bg-secondary/10 hover:text-secondary"
                                            onclick={() => { editingGroup = group; isGroupModalOpen = true; }}
                                        >
                                            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>
                                        </Button>
                                        <Button 
                                            variant="ghost" 
                                            circle 
                                            size="sm" 
                                            class="text-secondary hover:bg-secondary/10"
                                            onclick={() => { selectedGroupId = group.id!; isModifierModalOpen = true; }}
                                        >
                                            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" /></svg>
                                        </Button>
                                        <Button 
                                            variant="ghost" 
                                            circle 
                                            size="sm" 
                                            class="text-error hover:bg-error/10"
                                            onclick={() => { 
                                                if (group.id) {
                                                    handleDeleteGroup(group.id);
                                                } else {
                                                    alert('Error: ID no encontrado');
                                                }
                                            }}
                                            title="Eliminar Grupo"
                                        >
                                            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                                        </Button>
                                    </div>
                                </div>
                                
                                <div class="p-4 flex flex-col gap-2">
                                    {#if !group.modifiers || group.modifiers.length === 0}
                                        <p class="text-center py-8 text-[10px] italic opacity-30 uppercase font-black">Sin opciones configuradas</p>
                                    {:else}
                                        {#each group.modifiers as mod}
                                            <div class="flex items-center justify-between bg-base-200/30 p-3 rounded-2xl border border-transparent hover:border-secondary/20 transition-all group/item">
                                                <div class="flex items-center gap-3">
                                                    <div class="w-8 h-8 bg-secondary/10 rounded-lg flex items-center justify-center text-secondary font-black text-xs uppercase">
                                                        {mod.name[0]}
                                                    </div>
                                                    <div>
                                                        <p class="font-bold text-sm leading-tight">{mod.name}</p>
                                                        <p class="text-[9px] opacity-40 font-black uppercase">
                                                            {ingredients.find(i => i.id === mod.ingredient_id)?.name || 'Sin vínculo stock'}
                                                        </p>
                                                    </div>
                                                </div>
                                                <div class="flex items-center gap-3">
                                                    {#if mod.extra_price > 0}
                                                        <span class="text-[10px] font-black bg-secondary/10 text-secondary px-2 py-0.5 rounded-md">
                                                            +${mod.extra_price}
                                                        </span>
                                                    {/if}
                                                    <Button 
                                                        variant="ghost" 
                                                        circle 
                                                        size="xs" 
                                                        class="opacity-0 group-hover/item:opacity-100 hover:text-error"
                                                        onclick={() => handleDeleteModifier(mod.id!)}
                                                    >
                                                        <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                                                    </Button>
                                                </div>
                                            </div>
                                        {/each}
                                    {/if}
                                </div>
                            </div>
                        {/each}
                    </div>
                {/if}
            </div>
        </div>
    </div>
{/if}

<ModifierGroupModal 
    isOpen={isGroupModalOpen} 
    group={editingGroup} 
    onClose={() => isGroupModalOpen = false} 
    onSave={loadData}
/>

<ModifierModal 
    isOpen={isModifierModalOpen} 
    groupId={selectedGroupId} 
    {ingredients} 
    onClose={() => isModifierModalOpen = false} 
    onSave={loadData}
/>
