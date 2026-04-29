<script lang="ts">
    import type { Product, ModifierGroup } from '$lib/api/products';
    import Button from '../ui/Button.svelte';

    let { formData = $bindable(), availableModifierGroups } = $props<{
        formData: Partial<Product>;
        availableModifierGroups: ModifierGroup[];
    }>();
</script>

<div class="flex flex-col gap-6 animate-in fade-in slide-in-from-right-4">
    <div class="flex flex-col gap-4 bg-base-200/50 p-6 rounded-2xl border border-base-300">
        <h4 class="font-bold text-sm uppercase tracking-widest opacity-60">Vincular Grupos de Extras</h4>
        <div class="flex flex-wrap gap-2">
            {#each availableModifierGroups as group}
                {@const isLinked = formData.modifier_groups?.some(g => g.id === group.id)}
                <Button 
                    variant={isLinked ? 'primary' : 'outline'}
                    size="sm"
                    class={isLinked ? 'shadow-lg shadow-primary/20' : 'border-base-300'}
                    onclick={() => {
                        if (isLinked) {
                            formData.modifier_groups = formData.modifier_groups?.filter(g => g.id !== group.id);
                        } else {
                            formData.modifier_groups = [...(formData.modifier_groups || []), group];
                        }
                    }}
                >
                    {isLinked ? '✓' : '+'} {group.name}
                </Button>
            {/each}
            {#if availableModifierGroups.length === 0}
                <div class="alert alert-warning text-xs py-2 rounded-xl">
                    No hay grupos creados. Ve a Inventario para crear grupos como "Leches".
                </div>
            {/if}
        </div>
    </div>

    {#if !formData.modifier_groups || formData.modifier_groups.length === 0}
        <div class="py-12 text-center opacity-30 italic">
            <p>No hay grupos de extras vinculados.</p>
            <p class="text-xs">Selecciona arriba qué opciones (Leches, Jarabes, etc.) aplican a este producto.</p>
        </div>
    {:else}
        <div class="flex flex-col gap-4">
            {#each formData.modifier_groups as group}
                <div class="bg-base-100 p-6 rounded-2xl border border-base-200 shadow-sm">
                    <div class="flex justify-between items-center mb-4">
                        <h5 class="font-black text-lg tracking-tight text-primary flex items-center gap-2">
                            <div class="w-1 h-5 bg-primary rounded-full"></div>
                            {group.name}
                        </h5>
                        <span class="text-[10px] uppercase font-bold opacity-40 bg-base-200 px-3 py-1 rounded-full">
                            {group.modifiers?.length || 0} opciones
                        </span>
                    </div>
                    
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {#each group.modifiers || [] as mod}
                            <div class="bg-base-200/30 p-3 rounded-xl border border-base-300/50 flex justify-between items-center">
                                <span class="text-sm font-bold opacity-80">{mod.name}</span>
                                <div class="flex items-center gap-2">
                                    {#if mod.extra_price > 0}
                                        <span class="badge badge-sm badge-outline font-bold text-[10px] opacity-60">+${mod.extra_price}</span>
                                    {/if}
                                </div>
                            </div>
                        {/each}
                    </div>
                </div>
            {/each}
        </div>
    {/if}
</div>
