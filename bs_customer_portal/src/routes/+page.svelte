<script lang="ts">
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    
    onMount(() => {
        goto('/menu');
    });
</script>

<div style="text-align: center; padding: 2rem;">
    <h1>Cargando...</h1>
</div>
