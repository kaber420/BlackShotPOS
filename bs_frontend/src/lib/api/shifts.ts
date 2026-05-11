import { fetchApi } from '../api';

export interface ShiftInfo {
    id: number;
    register_id: number;
    start_time: string;
    end_time: string | null;
    status: 'OPEN' | 'CLOSED';
    initial_cash: number;
    expected_cash: number;
    expected_card: number;
    expected_transfer: number;
    actual_cash: number | null;
    actual_card: number | null;
    actual_transfer: number | null;
    difference_cash: number | null;
    notes: string | null;
}

export interface CashRegister {
    id: number;
    name: string;
    is_active: boolean;
}

export async function checkActiveShift() {
    return await fetchApi<{active: boolean, shift: ShiftInfo | null}>('/api/v1/pos/sales/shifts/active');
}

export async function getRegisters() {
    return await fetchApi<CashRegister[]>('/api/v1/pos/sales/shifts/registers');
}

export async function openShift(initialCash: number, registerId: number | null = null) {
    return await fetchApi<ShiftInfo>('/api/v1/pos/sales/shifts/open', {
        method: 'POST',
        body: JSON.stringify({ 
            initial_cash: initialCash,
            register_id: registerId
        })
    });
}

export async function closeShift(shiftId: number, data: {
    actual_cash: number,
    actual_card: number,
    actual_transfer: number,
    notes?: string
}) {
    return await fetchApi<ShiftInfo>(`/api/v1/pos/sales/shifts/${shiftId}/close`, {
        method: 'POST',
        body: JSON.stringify(data)
    });
}

export async function addCashMovement(shiftId: number, data: {
    amount: number,
    type: 'INCOME' | 'EXPENSE',
    reason: string
}) {
    return await fetchApi<any>(`/api/v1/pos/sales/shifts/${shiftId}/movement`, {
        method: 'POST',
        body: JSON.stringify(data)
    });
}

export async function getShiftReport(shiftId: number) {
    return await fetchApi<any>(`/api/v1/pos/sales/shifts/${shiftId}/report`);
}

export async function listShifts() {
    return await fetchApi<ShiftInfo[]>('/api/v1/pos/sales/shifts/');
}

export async function listActiveSessions() {
    return await fetchApi<ShiftInfo[]>('/api/v1/pos/sales/shifts/active-sessions');
}
