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
    nats_url: string;
    branch_id: string;
    menu_title: string;
    menu_subtitle: string;
    menu_logo_url?: string;
    menu_footer_text: string;
    menu_footer_tagline: string;
    menu_accent_color: string;
    menu_facebook_url?: string;
    menu_instagram_url?: string;
    menu_youtube_url?: string;
    menu_twitter_url?: string;
    menu_tiktok_url?: string;
    menu_whatsapp_url?: string;
}

export const SettingsService = {
    get: () => fetchApi<BusinessSettings>('/api/v1/pos/system/settings'),
    update: (settings: Partial<BusinessSettings>) => 
        fetchApi<BusinessSettings>('/api/v1/pos/system/settings', {
            method: 'PATCH',
            body: JSON.stringify(settings)
        })
};
