<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';

	let username = $state('');
	let password = $state('');
	let error = $state('');
	let loading = $state(false);

	// Funcióm para login normal
	async function handleLogin(e: Event) {
		e.preventDefault();
		loading = true;
		error = '';

		try {
			const res = await fetch('/api/_auth/login', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ username, password })
			});

			if (res.ok) {
				const data = await res.json();
				localStorage.setItem('X-Omni-Token', data.token);
				goto('/');
			} else {
				const data = await res.json();
				error = data.detail || 'Error de autenticación';
			}
		} catch (err) {
			error = 'Error de conexión con el servidor';
		} finally {
			loading = false;
		}
	}

	// Función para usar el Master Token (Atajo para desarrollo)
	function useMasterToken() {
		const masterToken = 'tu-token-super-seguro-aqui'; // Valor del .env por defecto
		localStorage.setItem('X-Omni-Token', masterToken);
		goto('/');
	}
</script>

<div class="min-h-screen bg-base-200 flex items-center justify-center p-4">
	<div class="card w-full max-w-md bg-base-100 shadow-xl overflow-hidden border border-base-300">
		<div class="card-body p-8">
			<div class="text-center mb-8">
				<h2 class="text-3xl font-black tracking-tight text-primary">BlackShot</h2>
				<p class="text-base-content/60 font-semibold mt-1">Acceso Administrativo</p>
			</div>

			{#if error}
				<div class="alert alert-error mb-6 shadow-sm">
					<svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
					<span>{error}</span>
				</div>
			{/if}

			<form onsubmit={handleLogin} class="space-y-4">
				<div class="form-control w-full">
					<label class="label pt-0" for="username">
						<span class="label-text font-bold">Usuario</span>
					</label>
					<input 
						id="username"
						type="text" 
						placeholder="admin" 
						class="input input-bordered w-full focus:input-primary transition-all font-medium" 
						bind:value={username}
						required
					/>
				</div>

				<div class="form-control w-full">
					<label class="label" for="password">
						<span class="label-text font-bold">Contraseña</span>
					</label>
					<input 
						id="password"
						type="password" 
						placeholder="••••••••" 
						class="input input-bordered w-full focus:input-primary transition-all font-medium" 
						bind:value={password}
						required
					/>
				</div>

				<div class="form-control mt-8">
					<button class="btn btn-primary btn-block text-lg shadow-md" disabled={loading}>
						{#if loading}
							<span class="loading loading-spinner"></span>
						{/if}
						Entrar al Sistema
					</button>
				</div>
			</form>

			<div class="divider my-8 text-xs opacity-50 font-bold uppercase tracking-widest">Desarrollo</div>

			<div class="text-center">
				<button onclick={useMasterToken} class="btn btn-outline btn-ghost btn-xs opacity-60 hover:opacity-100 transition-all italic underline">
					Usar Master Token de Emergencia
				</button>
			</div>
		</div>
	</div>
</div>
