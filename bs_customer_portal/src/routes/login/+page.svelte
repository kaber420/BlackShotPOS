<script lang="ts">
    import { goto } from '$app/navigation';
    
    let username = $state('');
    let password = $state('');
    let errorMsg = $state('');
    let loading = $state(false);
    
    async function handleLogin(e: Event) {
        e.preventDefault();
        loading = true;
        errorMsg = '';
        
        try {
            const res = await fetch(`/api/v1/public/customers/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Error de autenticación');
            }
            
            const data = await res.json();
            localStorage.setItem('customer_token', data.access_token);
            
            // Redirigir al menú en lugar del perfil si vienen por la carta
            goto('/menu');
        } catch (err: any) {
            errorMsg = err.message;
        } finally {
            loading = false;
        }
    }
</script>

<div class="min-h-[80vh] flex flex-col items-center justify-center px-4">
    <div class="w-full max-w-md bg-base-100/50 backdrop-blur-xl p-8 rounded-[2rem] border border-base-200 shadow-2xl">
        <div class="text-center mb-8">
            <h1 class="text-4xl font-black uppercase tracking-tighter mb-2">Iniciar Sesión</h1>
            <p class="text-xs uppercase tracking-[0.2em] font-bold opacity-40">Accede a la carta y beneficios</p>
        </div>
        
        {#if errorMsg}
            <div class="alert alert-error text-xs font-bold mb-6 rounded-xl">{errorMsg}</div>
        {/if}

        <form onsubmit={handleLogin} class="flex flex-col gap-5">
            <div class="form-control">
                <label class="label" for="username">
                    <span class="label-text text-[10px] uppercase font-black tracking-widest opacity-60">Nombre de Usuario</span>
                </label>
                <input 
                    type="text" 
                    id="username" 
                    bind:value={username} 
                    required 
                    placeholder="Ej. juanperez" 
                    class="input input-bordered input-lg w-full rounded-2xl bg-base-200/50 border-none focus:ring-2 focus:ring-primary/20 font-bold"
                />
            </div>
            
            <div class="form-control">
                <label class="label" for="password">
                    <span class="label-text text-[10px] uppercase font-black tracking-widest opacity-60">Contraseña</span>
                </label>
                <input 
                    type="password" 
                    id="password" 
                    bind:value={password} 
                    required
                    placeholder="Tu contraseña"
                    class="input input-bordered input-lg w-full rounded-2xl bg-base-200/50 border-none focus:ring-2 focus:ring-primary/20 font-bold"
                />
            </div>
            
            <button type="submit" class="btn btn-primary btn-lg w-full rounded-2xl mt-2 font-black uppercase tracking-widest" disabled={loading}>
                {#if loading}
                    <span class="loading loading-spinner"></span> Validando...
                {:else}
                    Ingresar
                {/if}
            </button>

            <div class="text-center text-[10px] uppercase tracking-wider font-bold opacity-30 mt-2 px-4">
                El registro es exclusivo en la caja física con el personal de la sucursal.
            </div>
        </form>
    </div>
</div>
