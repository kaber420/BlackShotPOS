<script lang="ts">
    import type { Snippet } from 'svelte';
    import type { HTMLButtonAttributes } from 'svelte/elements';

    let {
        type = 'button',
        variant = 'primary',
        disabled = false,
        children,
        class: className = '',
        onclick,
        ...rest
    }: {
        type?: 'button' | 'submit' | 'reset';
        variant?: 'primary' | 'secondary' | 'danger';
        disabled?: boolean;
        children?: Snippet;
        class?: string;
        onclick?: (event: MouseEvent) => void;
    } & HTMLButtonAttributes = $props();
</script>

<button {type} {disabled} class="btn btn-{variant} {className}" {onclick} {...rest}>
    {#if children}{@render children()}{/if}
</button>

<style>
    .btn {
        padding: 0.5rem 1rem;
        border-radius: 0.25rem;
        cursor: pointer;
        border: none;
        font-weight: bold;
    }
    .btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }
    .btn-primary {
        background-color: #000;
        color: #fff;
    }
</style>
