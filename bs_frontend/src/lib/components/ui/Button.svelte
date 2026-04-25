<script lang="ts">
    import type { Snippet } from 'svelte';

    interface Props {
        variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'success' | 'warning' | 'neutral';
        size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
        type?: 'button' | 'submit' | 'reset';
        disabled?: boolean;
        isLoading?: boolean;
        square?: boolean;
        circle?: boolean;
        class?: string;
        children?: Snippet;
        icon?: Snippet;
        iconPosition?: 'left' | 'right';
        id?: string;
        title?: string;
        onclick?: (e: MouseEvent) => void;
    }

    let {
        variant = 'primary',
        size = 'md',
        type = 'button',
        disabled = false,
        isLoading = false,
        square = false,
        circle = false,
        class: className = '',
        children,
        icon,
        iconPosition = 'left',
        id,
        title,
        onclick,
        ...rest
    }: Props = $props();

    const variantClasses = {
        primary: 'btn-primary text-white',
        secondary: 'btn-secondary',
        outline: 'btn-outline', // Ya estilizado en app.css para usar primary
        ghost: 'btn-ghost',
        danger: 'btn-error text-white',
        success: 'btn-success text-white',
        warning: 'btn-warning text-white',
        neutral: 'btn-neutral'
    };

    const sizeClasses = {
        xs: 'btn-xs h-8 min-h-0 px-2 text-[10px]',
        sm: 'btn-sm h-10 min-h-0 px-3 text-xs',
        md: 'btn-md h-12 px-5 text-sm',
        lg: 'btn-lg h-16 px-8 text-base',
        xl: 'btn-xl h-20 px-10 text-lg'
    };

    let combinedClasses = $derived([
        'btn',
        variantClasses[variant] || '',
        sizeClasses[size] || '',
        square ? 'btn-square' : '',
        circle ? 'btn-circle' : '',
        isLoading ? 'btn-disabled opacity-80 cursor-not-allowed' : '',
        className
    ].filter(Boolean).join(' '));
</script>

<button
    {type}
    class={combinedClasses}
    disabled={disabled || isLoading}
    {id}
    {title}
    {onclick}
    {...rest}
>
    {#if isLoading}
        <span class="loading loading-spinner {size === 'xs' || size === 'sm' ? 'loading-xs' : 'loading-sm'}"></span>
    {:else}
        {#if icon && iconPosition === 'left'}
            {@render icon()}
        {/if}
        
        {#if children}
            {@render children()}
        {/if}

        {#if icon && iconPosition === 'right'}
            {@render icon()}
        {/if}
    {/if}
</button>

<style>
    /* Estilos adicionales específicos del botón Blackshot si no se cubrieron en app.css */
    button {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        user-select: none;
    }
    
    /* Animación de pulsado suave */
    button:active {
        transform: scale(0.96);
    }
</style>
