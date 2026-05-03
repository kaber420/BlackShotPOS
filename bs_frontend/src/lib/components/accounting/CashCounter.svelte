<script lang="ts">
    interface Props {
        onTotalChange?: (total: number) => void;
        initialTotal?: number;
    }

    let { onTotalChange, initialTotal = 0 }: Props = $props();

    const denominations = [
        { value: 1000, label: 'Billetes $1000', type: 'bill' },
        { value: 500, label: 'Billetes $500', type: 'bill' },
        { value: 200, label: 'Billetes $200', type: 'bill' },
        { value: 100, label: 'Billetes $100', type: 'bill' },
        { value: 50, label: 'Billetes $50', type: 'bill' },
        { value: 20, label: 'Billetes $20', type: 'bill' },
        { value: 10, label: 'Monedas $10', type: 'coin' },
        { value: 5, label: 'Monedas $5', type: 'coin' },
        { value: 2, label: 'Monedas $2', type: 'coin' },
        { value: 1, label: 'Monedas $1', type: 'coin' },
        { value: 0.5, label: 'Monedas $0.50', type: 'coin' },
    ];

    let counts = $state(Object.fromEntries(denominations.map(d => [d.value, 0])));

    let total = $derived(
        Object.entries(counts).reduce((acc, [value, count]) => acc + (parseFloat(value) * count), 0)
    );

    $effect(() => {
        onTotalChange?.(total);
    });

    function clear() {
        Object.keys(counts).forEach(k => counts[parseFloat(k)] = 0);
    }
</script>

<div class="bg-base-200/50 p-4 rounded-2xl border border-base-300">
    <div class="flex justify-between items-center mb-4">
        <h4 class="font-black text-lg uppercase tracking-wider text-base-content/70">Calculadora de Efectivo</h4>
        <button class="btn btn-ghost btn-xs text-error font-bold" onclick={clear}>Limpiar Todo</button>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="space-y-2">
            <h5 class="text-xs font-black opacity-50 uppercase mb-2">Billetes</h5>
            {#each denominations.filter(d => d.type === 'bill') as d}
                <div class="flex items-center gap-2">
                    <div class="w-24 text-sm font-bold text-base-content/80">{d.label}</div>
                    <div class="join flex-1">
                        <button 
                            class="join-item btn btn-square btn-sm" 
                            onclick={() => counts[d.value] = Math.max(0, counts[d.value] - 1)}
                        >-</button>
                        <input 
                            type="number" 
                            min="0" 
                            bind:value={counts[d.value]} 
                            class="join-item input input-bordered input-sm w-full text-center font-black" 
                        />
                        <button 
                            class="join-item btn btn-square btn-sm" 
                            onclick={() => counts[d.value]++}
                        >+</button>
                    </div>
                </div>
            {/each}
        </div>

        <div class="space-y-2">
            <h5 class="text-xs font-black opacity-50 uppercase mb-2">Monedas</h5>
            {#each denominations.filter(d => d.type === 'coin') as d}
                <div class="flex items-center gap-2">
                    <div class="w-24 text-sm font-bold text-base-content/80">{d.label}</div>
                    <div class="join flex-1">
                        <button 
                            class="join-item btn btn-square btn-sm" 
                            onclick={() => counts[d.value] = Math.max(0, counts[d.value] - 1)}
                        >-</button>
                        <input 
                            type="number" 
                            min="0" 
                            bind:value={counts[d.value]} 
                            class="join-item input input-bordered input-sm w-full text-center font-black" 
                        />
                        <button 
                            class="join-item btn btn-square btn-sm" 
                            onclick={() => counts[d.value]++}
                        >+</button>
                    </div>
                </div>
            {/each}
        </div>
    </div>

    <div class="mt-6 p-4 bg-primary/10 rounded-xl border border-primary/20 flex justify-between items-center">
        <span class="font-black text-primary uppercase tracking-widest text-sm">Total Contado:</span>
        <span class="text-3xl font-black text-primary">${total.toLocaleString('es-MX', { minimumFractionDigits: 2 })}</span>
    </div>
</div>
