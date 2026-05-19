<script lang="ts">
    import type { HTMLImgAttributes } from 'svelte/elements';

    let {
        src,
        alt = '',
        class: className = '',
        ...rest
    }: {
        src: string;
        alt?: string;
        class?: string;
    } & HTMLImgAttributes = $props();
    
    let fullUrl = $derived(src);
</script>

<img src={fullUrl} {alt} class="w-full h-full object-cover {className}" {...rest} />
