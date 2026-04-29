<script lang="ts">
    import type { Product } from '$lib/api/products';
    import { marked } from 'marked';

    let { formData = $bindable() } = $props<{
        formData: Partial<Product>;
    }>();
</script>

<div class="flex flex-col gap-6 animate-in fade-in slide-in-from-bottom-2">
    <div class="bg-primary/5 p-6 rounded-2xl border border-primary/20">
        <h4 class="text-xl font-black mb-4 flex items-center gap-2 text-primary">
            📖 Instrucciones de Preparación
        </h4>
        <div class="form-control">
            <label class="label font-bold text-xs uppercase tracking-widest opacity-60">Receta (Markdown)</label>
            <textarea 
                class="textarea textarea-bordered h-64 focus:textarea-primary font-mono text-sm" 
                placeholder="Escribe los pasos de preparación aquí...
Ej:
1. Calentar la leche a 60°C.
2. Extraer el shot de espresso.
3. Mezclar suavemente." 
                bind:value={formData.recipe_markdown}
            ></textarea>
        </div>
        <div class="mt-4 p-4 bg-base-100 rounded-xl border border-base-300">
            <h5 class="text-[10px] font-black uppercase opacity-40 mb-2">Previsualización rápida</h5>
            <!-- svelte-ignore a11y_click_events_have_key_events -->
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div class="prose prose-sm max-w-none opacity-70 bg-base-200/50 p-4 rounded-lg min-h-[100px] recipe-preview-area"
                onclick={(e) => {
                    const li = (e.target as HTMLElement).closest('li');
                    if (li) {
                        const checkbox = li.querySelector('input[type="checkbox"]') as HTMLInputElement;
                        if (checkbox && e.target !== checkbox) {
                            checkbox.checked = !checkbox.checked;
                        }
                    }
                }}
            >
                {#if formData.recipe_markdown}
                    {@html marked(formData.recipe_markdown).toString().replace(/<input disabled="" type="checkbox">/g, '<input type="checkbox" class="checkbox checkbox-primary checkbox-xs mr-2">')}
                {:else}
                    <p class="italic text-xs opacity-50">Sin instrucciones todavía. Escribe algo arriba para ver la vista previa.</p>
                {/if}
            </div>

            <style>
                .recipe-preview-area :global(li:has(input:checked)) {
                    text-decoration: line-through;
                    opacity: 0.5;
                }
                .recipe-preview-area :global(input[type="checkbox"]) {
                    pointer-events: auto;
                    cursor: pointer;
                }
            </style>
        </div>
    </div>
</div>
