import { fetchApi } from '../api';

export interface BusinessSettings {
    id: number;
    name: string;
    address?: string;
    phone?: string;
    tax_rate: number;
    currency_symbol: string;
    currency_code: string;
    locale: string;
    ticket_footer?: string;
    bridge_enabled: boolean;
    bridge_public_key?: string;
}

export const SettingsService = {
    get: () => fetchApi<BusinessSettings>('/api/v1/pos/settings'),
    update: (settings: Partial<BusinessSettings>) => 
        fetchApi<BusinessSettings>('/api/v1/pos/settings', {
            method: 'PATCH',
            body: JSON.stringify(settings)
        })
};
