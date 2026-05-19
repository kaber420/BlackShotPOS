<script lang="ts">
    import { goto } from '$app/navigation';
</script>

<div class="min-h-[80vh] flex flex-col items-center justify-center px-4">
    <div class="w-full max-w-md bg-base-100/50 backdrop-blur-xl p-8 rounded-[2rem] border border-base-200 shadow-2xl text-center">
        <div class="w-20 h-20 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-6 text-primary border border-primary/20">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 00-2 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
        </div>
        
        <h1 class="text-3xl font-black uppercase tracking-tighter mb-4">Registro Exclusivo</h1>
        <p class="text-sm font-medium opacity-70 mb-6 leading-relaxed">
            Para garantizar la seguridad de tus datos y la integridad de nuestro programa de lealtad, el registro de nuevas cuentas se realiza de forma exclusiva por nuestro personal en la caja.
        </p>

        <div class="bg-base-200/50 p-5 rounded-2xl border border-base-200/50 text-left mb-6">
            <h3 class="text-xs uppercase font-black tracking-wider mb-2 opacity-80">¿Cómo registrarse?</h3>
            <ol class="text-xs space-y-2 opacity-70 list-decimal pl-4">
                <li>Acércate al mostrador principal o caja física de la sucursal.</li>
                <li>Pide al cajero que te dé de alta en el sistema Blackshot.</li>
                <li>Proporciona tu nombre, teléfono y un nombre de usuario de tu elección.</li>
                <li>¡Listo! El cajero te proporcionará una contraseña para que puedas iniciar sesión inmediatamente en tu dispositivo móvil.</li>
            </ol>
        </div>
        
        <button onclick={() => goto('/login')} class="btn btn-primary btn-lg w-full rounded-2xl font-black uppercase tracking-widest">
            Volver al Inicio de Sesión
        </button>
    </div>
</div>
