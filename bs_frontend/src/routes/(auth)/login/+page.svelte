<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { setAuth, initAuth } from '$lib/app_state.svelte';
	import { PUBLIC_API_URL } from '$env/static/public';
	import Button from '$lib/components/ui/Button.svelte';

	let email = $state('');
	let password = $state('');
	let error = $state('');
	let loading = $state(false);

	// Funcióm para login normal
	async function handleLogin(e: Event) {
		e.preventDefault();
		loading = true;
		error = '';

		try {
			const formData = new URLSearchParams();
			formData.append('username', email); // FastAPI Users espera 'username' como email
			formData.append('password', password);

			const res = await fetch(`${PUBLIC_API_URL}/api/auth/jwt/login`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
				credentials: 'include',
				body: formData
			});

			if (res.ok) {
				const success = await initAuth();
				if (success) {
					goto('/');
				} else {
					error = 'Error al cargar perfil tras login';
				}
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
					<label class="label pt-0" for="email">
						<span class="label-text font-bold">Correo Electrónico</span>
					</label>
					<input 
						id="email"
						type="email" 
						placeholder="admin@blackshot.pos" 
						class="input input-bordered w-full focus:input-primary transition-all font-medium" 
						bind:value={email}
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
					<Button 
						variant="primary" 
						size="lg" 
						class="w-full text-lg shadow-md" 
						disabled={loading}
						isLoading={loading}
						type="submit"
					>
						Entrar al Sistema
					</Button>
				</div>
			</form>
		</div>
	</div>
</div>
