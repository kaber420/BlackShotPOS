<script lang="ts">
	let { children } = $props();
</script>

<div class="min-h-screen bg-base-200">
	{@render children()}
</div>
