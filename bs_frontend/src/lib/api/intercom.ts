import { fetchApi } from '../api';

export interface IntercomMessage {
    id: number;
    sender_name: string;
    audio_url: string;
    is_global: boolean;
    target_areas: number[];
    timestamp: string;
}

export const IntercomService = {
    sendVoiceMessage: async (audioBlob: Blob, areaIds: number[], isGlobal: boolean = false) => {
        const formData = new FormData();
        formData.append('audio', audioBlob, 'voice.webm');
        if (areaIds.length > 0) {
            formData.append('area_ids', areaIds.join(','));
        }
        formData.append('is_global', isGlobal.toString());

        return fetchApi<IntercomMessage>('/api/v1/pos/communications/voice', {
            method: 'POST',
            body: formData,
        });
    },

    getHistory: () => fetchApi<IntercomMessage[]>('/api/v1/pos/communications/history')
};
