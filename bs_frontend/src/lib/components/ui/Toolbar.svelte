<script lang="ts">
    import type { Snippet } from 'svelte';

    interface Props {
        title: string;
        left?: Snippet;
        right?: Snippet;
    }

    let { title, left, right }: Props = $props();
</script>

<div class="flex items-center justify-between bg-base-100 shadow-sm p-2 rounded-xl border border-base-200 shrink-0 gap-4">
    <div class="flex items-center gap-4 flex-1 px-2">
        <h1 class="text-xl font-black tracking-tight uppercase opacity-80 shrink-0">{title}</h1>
        
        <div class="h-6 w-[1px] bg-base-300 mx-2 hidden lg:block"></div>

        {#if left}
            {@render left()}
        {/if}
    </div>

    {#if right}
        <div class="flex items-center gap-2 pr-2">
            {@render right()}
        </div>
    {/if}
</div>
