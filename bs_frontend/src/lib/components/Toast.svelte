<script>
    /**
     * Blackshot POS - Toast Notification Component
     * -------------------------------------------
     * A clean, robust toast renderer for professional applications.
     */
    import { toastState, toastConfig, removeToast } from '$lib/toast.svelte.js';
    import { fly, fade } from 'svelte/transition';
    import { flip } from 'svelte/animate';
</script>

<div class="toast-container {toastConfig.position}">
    {#each toastState.toasts as toast (toast.id)}
        <div 
            animate:flip={{duration: 300}}
            class="toast-wrapper"
        >
            <div 
                in:fly={{ y: toastConfig.position.includes('top') ? -20 : 20, duration: 300 }}
                out:fade={{ duration: 200 }}
                role="alert"
                class="toast-item shape-{toastConfig.shape} {toast.type}"
                onclick={() => removeToast(toast.id)}
                onkeydown={(e) => e.key === 'Enter' && removeToast(toast.id)}
                tabindex="0"
                style="
                    --bg-color: {toastConfig.backgroundColor};
                    --bg-opacity: {toastConfig.backgroundOpacity}%;
                    --text-color: {toastConfig.textColor};
                    --blur: {toastConfig.blur}px;
                    --shadow: {toastConfig.hasShadow ? 'drop-shadow(0 8px 25px rgba(0,0,0,0.4))' : 'none'};
                    --font-size: {toastConfig.fontSize};
                "
            >
                <div class="toast-content">
                    <span class="icon">
                        {#if toast.type === 'success'}
                            ✓
                        {:else if toast.type === 'error'}
                            !
                        {:else}
                            i
                        {/if}
                    </span>
                    <span class="message">{toast.message}</span>
                </div>
            </div>
        </div>
    {/each}
</div>

<style>
    /* Fixed base container */
    .toast-container {
        position: fixed;
        display: flex;
        flex-direction: column;
        gap: 0.85rem;
        z-index: 10000;
        pointer-events: none;
        max-width: 450px;
        width: calc(100% - 2rem);
    }

    /* Position Mapping */
    .toast-container.bottom-right { bottom: 2rem; right: 2rem; align-items: flex-end; }
    .toast-container.bottom-center { bottom: 2rem; left: 50%; transform: translateX(-50%); align-items: center; }
    .toast-container.bottom-left { bottom: 2rem; left: 2rem; align-items: flex-start; }
    .toast-container.top-right { top: 2rem; right: 2rem; align-items: flex-end; }
    .toast-container.top-center { top: 2rem; left: 50%; transform: translateX(-50%); align-items: center; }
    .toast-container.top-left { top: 2rem; left: 2rem; align-items: flex-start; }

    .toast-wrapper {
        display: flex;
        flex-direction: column;
        width: fit-content;
    }

    /* Main Item Styling */
    .toast-item {
        pointer-events: auto;
        padding: 0.85rem 1.75rem;
        background-color: color-mix(in srgb, var(--bg-color), transparent calc(100% - var(--bg-opacity)));
        backdrop-filter: blur(var(--blur));
        -webkit-backdrop-filter: blur(var(--blur));
        color: var(--text-color);
        cursor: pointer;
        filter: var(--shadow);
        border: 1px solid rgba(255, 255, 255, 0.1);
        display: flex;
        align-items: center;
        transition: transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }

    .toast-item:hover {
        transform: scale(1.02);
    }

    /* Shapes */
    .shape-bean { 
        border-radius: 40px 10px 40px 10px; 
    }
    .shape-square { 
        border-radius: 16px; 
    }

    /* Message Content Layout */
    .toast-content {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        font-weight: 700;
        width: 100%;
        font-size: var(--font-size);
    }

    .icon {
        background: rgba(255, 255, 255, 0.2);
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        flex-shrink: 0;
        font-size: 1rem;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
    }

    .message {
        line-height: 1.25;
        flex: 1;
        word-break: break-word;
        overflow-wrap: anywhere;
    }

    /* Type Specific Overrides */
    .toast-item.error {
        background-color: #991b1b !important; /* Proper error red */
        color: #fff !important;
        border-color: rgba(255,255,255,0.2);
    }
    .toast-item.error .icon {
        background: rgba(0,0,0,0.2);
    }
</style>
