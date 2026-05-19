const BASE = '/api/users';

function authHeaders() {
    return { 'Content-Type': 'application/json' };
}

export interface PosUser {
    uuid: string;
    username: string;
    role: string;
    is_active: number;
    mfa_enabled: boolean;
    created_at: string;
    permissions?: Record<string, boolean>;
}

export interface CreateUserPayload {
    username: string;
    password: string;
    role: string;
    enable_mfa?: boolean;
}

export const UserService = {
    async list(includeInactive = false): Promise<PosUser[]> {
        const res = await fetch(`${BASE}?include_inactive=${includeInactive}`, {
            headers: authHeaders(),
            credentials: 'include'
        });
        if (!res.ok) throw new Error('Error listando usuarios');
        return res.json();
    },

    async get(uuid: string): Promise<PosUser> {
        const res = await fetch(`${BASE}/${uuid}`, { 
            headers: authHeaders(),
            credentials: 'include'
        });
        if (!res.ok) throw new Error('Usuario no encontrado');
        return res.json();
    },

    async create(payload: any): Promise<PosUser> {
        const res = await fetch(`/api/auth/register`, {
            method: 'POST',
            headers: authHeaders(),
            credentials: 'include',
            body: JSON.stringify(payload),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail ?? 'Error creando usuario');
        }
        return res.json();
    },

    async update(uuid: string, data: any): Promise<void> {
        const res = await fetch(`${BASE}/${uuid}`, {
            method: 'PATCH',
            headers: authHeaders(),
            credentials: 'include',
            body: JSON.stringify(data),
        });
        if (!res.ok) throw new Error('Error actualizando usuario');
    },

    async setPermission(uuid: string, perm: string, value: boolean): Promise<void> {
        const res = await fetch(`${BASE}/${uuid}/permissions`, {
            method: 'PATCH',
            headers: authHeaders(),
            body: JSON.stringify({ [perm]: value }),
        });
        if (!res.ok) throw new Error('Error actualizando permiso');
    },

    async resetPermission(uuid: string, perm: string): Promise<void> {
        const res = await fetch(`${BASE}/${uuid}/permissions/${perm}`, {
            method: 'DELETE',
            headers: authHeaders(),
        });
        if (!res.ok) throw new Error('Error reseteando permiso');
    },

    async changePassword(uuid: string, newPassword: string): Promise<void> {
        const res = await fetch(`${BASE}/${uuid}/password`, {
            method: 'PUT',
            headers: authHeaders(),
            body: JSON.stringify({ new_password: newPassword }),
        });
        if (!res.ok) throw new Error('Error cambiando contraseña');
    },

    async deactivate(uuid: string): Promise<void> {
        const res = await fetch(`${BASE}/${uuid}`, {
            method: 'DELETE',
            headers: authHeaders(),
        });
        if (!res.ok) throw new Error('Error desactivando usuario');
    },

    async activate(uuid: string): Promise<void> {
        await UserService.update(uuid, { is_active: 1 });
    },
};
