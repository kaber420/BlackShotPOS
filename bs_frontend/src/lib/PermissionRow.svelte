<script lang="ts">
    import { UserService } from '$lib/api/users';
    import { ROLE_PRESETS_JS } from '$lib/roles';

    interface Props {
        permission: { key: string; label: string; desc: string };
        userUuid: string;
        userRole: string;
        onFlash: (msg: string) => void;
        onError: (msg: string) => void;
    }

    let { permission, userUuid, userRole, onFlash, onError }: Props = $props();

    // El default del rol para este permiso
    let roleDefault = $derived(ROLE_PRESETS_JS[userRole]?.[permission.key] ?? true);

    let override = $state<boolean | null>(null); // null = sin override (usa el del rol)
    let saving = $state(false);

    // El valor efectivo que se muestra
    let effective = $derived(override !== null ? override : roleDefault);

    async function toggle() {
        saving = true;
        const newVal = !effective;
        try {
            if (newVal === roleDefault) {
                // Igual al default del rol → resetear override
                await UserService.resetPermission(userUuid, permission.key);
                override = null;
            } else {
                await UserService.setPermission(userUuid, permission.key, newVal);
                override = newVal;
            }
            onFlash(`Permiso "${permission.label}" ${newVal ? 'activado' : 'desactivado'}`);
        } catch (e: any) {
            onError(e.message);
        } finally {
            saving = false;
        }
    }
</script>

<div class="flex items-center justify-between p-3 rounded-xl border
    {override !== null ? 'border-warning/40 bg-warning/5' : 'border-base-200 bg-base-200/30'}
    hover:bg-base-200/60 transition-colors">
    <div class="flex-1 min-w-0">
        <p class="font-bold text-sm leading-tight">{permission.label}</p>
        <p class="text-xs opacity-50 truncate">{permission.desc}</p>
        {#if override !== null}
            <span class="badge badge-warning badge-xs mt-1">override</span>
        {/if}
    </div>
    <button
        class="btn btn-sm ml-3 {effective ? 'btn-success' : 'btn-ghost opacity-40'}"
        onclick={toggle}
        disabled={saving}
        title="{effective ? 'Activo — click para desactivar' : 'Inactivo — click para activar'}"
    >
        {#if saving}
            <span class="loading loading-spinner loading-xs"></span>
        {:else}
            {effective ? '✓' : '✕'}
        {/if}
    </button>
</div>
