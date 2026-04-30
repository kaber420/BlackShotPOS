from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pydantic import BaseModel

from pos_core.database import get_session
from pos_core.auth.dependencies import require_permission
from pos_core.roles import Permission
from .service import open_shift, close_shift, get_active_shift, get_shift_report, list_shifts

router = APIRouter()

class OpenShiftRequest(BaseModel):
    initial_cash: float

class CloseShiftRequest(BaseModel):
    actual_cash: float

@router.post("/open")
async def api_open_shift(
    req: OpenShiftRequest,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.MANAGE_SHIFTS)),
):
    """Abre un nuevo turno de caja con el fondo inicial indicado."""
    shift = await open_shift(session, req.initial_cash)
    return shift

@router.post("/{shift_id}/close")
async def api_close_shift(
    shift_id: int,
    req: CloseShiftRequest,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.MANAGE_SHIFTS)),
):
    """Cierra el turno especificado registrando el efectivo físico contado."""
    shift = await close_shift(session, shift_id, req.actual_cash)
    return shift

@router.get("/active")
async def api_get_active_shift(session: AsyncSession = Depends(get_session)):
    """Devuelve el turno actualmente abierto, o {active: false} si no hay ninguno."""
    shift = await get_active_shift(session)
    if not shift:
        return {"active": False, "shift": None}
    return {"active": True, "shift": shift}

@router.get("/")
async def api_list_shifts(
    session: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.MANAGE_SHIFTS)),
):
    """
    Lista todos los turnos históricos (abiertos y cerrados).
    Incluye totales de ventas por método de pago, conteo de órdenes y duración.
    Ordenados del más reciente al más antiguo.
    """
    return await list_shifts(session)

@router.get("/{shift_id}/report")
async def api_get_shift_report(
    shift_id: int,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.MANAGE_SHIFTS)),
):
    """
    Reporte completo y auditable de un turno específico.
    Incluye totales financieros y la lista de todas las órdenes procesadas.
    """
    report = await get_shift_report(session, shift_id)
    return report
