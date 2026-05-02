import { fetchApi } from '../api';

export interface ShiftInfo {
    id: number;
    start_time: string;
    end_time: string;
    status: 'OPEN' | 'CLOSED';
    initial_cash: number;
    expected_cash: number;
    actual_cash: number | null;
    difference: number | null;
}

export async function checkActiveShift() {
    return await fetchApi<{active: boolean, shift: ShiftInfo | null}>('/api/v1/pos/sales/shifts/active');
}

export async function openShift(initialCash: number) {
    return await fetchApi<ShiftInfo>('/api/v1/pos/sales/shifts/open', {
        method: 'POST',
        body: JSON.stringify({ initial_cash: initialCash })
    });
}

export async function closeShift(shiftId: number, actualCash: number) {
    return await fetchApi<ShiftInfo>(`/api/v1/pos/sales/shifts/${shiftId}/close`, {
        method: 'POST',
        body: JSON.stringify({ actual_cash: actualCash })
    });
}

export async function getShiftReport(shiftId: number) {
    return await fetchApi<any>(`/api/v1/pos/sales/shifts/${shiftId}/report`);
}
