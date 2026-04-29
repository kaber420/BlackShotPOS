<script lang="ts">
    import type { Product } from '$lib/api/products';

    let { formData = $bindable() } = $props<{
        formData: Partial<Product>;
    }>();
</script>

<div class="bg-base-200/30 p-8 rounded-2xl border border-base-300 animate-in fade-in zoom-in-95">
    <h4 class="text-xl font-bold mb-6 flex items-center gap-2">
            Estimaciones Nutricionales (Por Porción Base)
    </h4>
    <div class="grid grid-cols-2 md:grid-cols-4 gap-6">
        <div class="form-control">
            <label class="label font-bold text-xs uppercase opacity-60 text-primary">Proteína (g)</label>
            <input type="number" class="input input-bordered text-center font-mono text-lg" bind:value={formData.protein} />
        </div>
        <div class="form-control">
            <label class="label font-bold text-xs uppercase opacity-60 text-orange-500">Calorías (kcal)</label>
            <input type="number" class="input input-bordered text-center font-mono text-lg" bind:value={formData.calories} />
        </div>
        <div class="form-control">
            <label class="label font-bold text-xs uppercase opacity-60 text-blue-500">Carbos (g)</label>
            <input type="number" class="input input-bordered text-center font-mono text-lg" bind:value={formData.carbs} />
        </div>
        <div class="form-control">
            <label class="label font-bold text-xs uppercase opacity-60 text-emerald-500">Grasas (g)</label>
            <input type="number" class="input input-bordered text-center font-mono text-lg" bind:value={formData.fats} />
        </div>
    </div>
    <p class="mt-6 text-sm opacity-50 italic">
        * Estos valores se usarán como referencia general. Puedes sobreescribirlos por tamaño en la sección "Tallas".
    </p>
</div>
