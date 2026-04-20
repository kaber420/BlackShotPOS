import { fetchApi } from '../api';

const BASE_URL = '/api/v1/pos/admin/iot';

export const IoTService = {
    async listDevices() {
        return fetchApi<any[]>(`${BASE_URL}/devices`);
    },

    async createDevice(data: { device_id: string, name?: string, type?: string, table_id?: number | null }) {
        return fetchApi<any>(`${BASE_URL}/devices`, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async updateDevice(id: number, data: any) {
        return fetchApi<any>(`${BASE_URL}/devices/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
    },

    async rotateToken(id: number) {
        return fetchApi<{token: string}>(`${BASE_URL}/devices/${id}/rotate-token`, {
            method: 'POST'
        });
    },

    async deleteDevice(id: number) {
        return fetchApi<any>(`${BASE_URL}/devices/${id}`, {
            method: 'DELETE'
        });
    }
};
