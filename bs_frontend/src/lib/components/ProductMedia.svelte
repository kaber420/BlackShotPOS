<script lang="ts">
    import { onMount } from 'svelte';

    interface Props {
        src: string;
        alt: string;
        class?: string;
    }

    let { src, alt, class: className = '' }: Props = $props();

    // Detectar si es WebM (para activar lógica de activación)
    let isWebM = $derived(src.toLowerCase().endsWith('.webm'));
    
    let videoElement = $state<HTMLVideoElement | null>(null);
    let isHovered = $state(false);
    let isVisible = $state(false);
    let container = $state<HTMLElement | null>(null);

    // Lógica de reproducción inteligente para WebM
    $effect(() => {
        if (!videoElement || !isWebM) return;

        if (isHovered || isVisible) {
            videoElement.play().catch(() => {
                // Manejar bloqueo de autoplay si el navegador lo requiere
            });
        } else {
            videoElement.pause();
            // Opcional: Reiniciar al primer frame para efecto de "foto que despierta"
            videoElement.currentTime = 0;
        }
    });

    onMount(() => {
        if (!container || !isWebM) return;

        // IntersectionObserver para detectar cuando el producto está en el centro (Mobile)
        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    // Se activa cuando está al menos al 50% visible
                    isVisible = entry.isIntersecting && entry.intersectionRatio > 0.5;
                });
            },
            {
                threshold: [0, 0.5, 1.0]
            }
        );

        observer.observe(container);
        return () => observer.disconnect();
    });
</script>

<div 
    bind:this={container}
    class="relative w-full h-full overflow-hidden {className}"
    onmouseenter={() => isHovered = true}
    onmouseleave={() => isHovered = false}
    role="presentation"
>
    {#if isWebM}
        <!-- svelte-ignore a11y_media_has_caption -->
        <video
            bind:this={videoElement}
            {src}
            muted
            loop
            playsinline
            class="w-full h-full object-cover transition-transform duration-700 {isHovered ? 'scale-110' : 'scale-100'}"
        ></video>
        
        <!-- Indicador sutil de que es un "cinemagraph" cuando está pausado -->
        {#if !isHovered && !isVisible}
            <div class="absolute top-3 right-3 bg-black/20 backdrop-blur-sm p-1.5 rounded-full opacity-60 pointer-events-none transition-opacity duration-300">
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                    <polygon points="5 3 19 12 5 21 5 3"></polygon>
                </svg>
            </div>
        {/if}
    {:else}
        <!-- Para WebP, PNG, JPG, etc. se comporta como imagen normal -->
        <img 
            {src} 
            {alt} 
            class="w-full h-full object-cover transition-transform duration-700 {className.includes('group-hover') || isHovered ? 'scale-110' : 'scale-100'}"
            loading="lazy"
        />
    {/if}
</div>

<style>
    video {
        /* Evita parpadeos al cargar */
        background: transparent;
    }
</style>
