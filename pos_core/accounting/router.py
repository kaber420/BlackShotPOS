from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from pydantic import BaseModel
from uuid import UUID

from pos_core.database import get_session
from pos_core.auth.dependencies import require_permission
from pos_core.roles import Permission
from .service import (
    open_shift, close_shift, get_active_shift, get_shift_report, list_shifts,
    get_cash_registers, create_cash_register, add_cash_movement, get_all_active_shifts,
    enrich_shift_data, get_movement_categories, create_movement_category
)
from .models import CashMovementType

router = APIRouter()

# --- SCHEMAS ---

class CreateRegisterRequest(BaseModel):
    name: str

class OpenShiftRequest(BaseModel):
    initial_cash: float
    register_id: Optional[int] = None

class CloseShiftRequest(BaseModel):
    actual_cash: float
    actual_card: float = 0.0
    actual_transfer: float = 0.0
    notes: Optional[str] = None

class CashMovementRequest(BaseModel):
    amount: float
    type: CashMovementType
    reason: str
    category_id: Optional[int] = None

class CreateMovementCategoryRequest(BaseModel):
    name: str
    type: CashMovementType
    description: Optional[str] = None

# --- MOVEMENT CATEGORIES ---

@router.get("/movement-categories")
async def api_get_movement_categories(
    session: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.MANAGE_SHIFTS)),
):
    """Lista todas las categorías de movimiento disponibles."""
    return await get_movement_categories(session)

@router.post("/movement-categories")
async def api_create_movement_category(
    req: CreateMovementCategoryRequest,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.MANAGE_SHIFTS)),
):
    """Crea una nueva categoría de movimiento."""
    return await create_movement_category(session, req.name, req.type, req.description)

# --- REGISTERS ---

@router.get("/registers")
async def api_get_registers(
    session: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.MANAGE_SHIFTS)),
):
    """Lista las cajas (puntos de venta) activas."""
    return await get_cash_registers(session)

@router.post("/registers")
async def api_create_register(
    req: CreateRegisterRequest,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.MANAGE_SHIFTS)),
):
    """Crea una nueva caja registradora."""
    return await create_cash_register(session, req.name)

# --- SHIFTS ---

@router.post("/open")
async def api_open_shift(
    req: OpenShiftRequest,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.MANAGE_SHIFTS)),
):
    """Abre un nuevo turno de caja en una caja específica."""
    shift = await open_shift(session, req.initial_cash, user.id, req.register_id)
    return shift

@router.post("/{shift_id}/close")
async def api_close_shift(
    shift_id: int,
    req: CloseShiftRequest,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.MANAGE_SHIFTS)),
):
    """Cierra el turno especificando los totales físicos contados."""
    shift = await close_shift(
        session, 
        shift_id, 
        req.actual_cash, 
        req.actual_card, 
        req.actual_transfer, 
        req.notes
    )
    return shift

@router.post("/{shift_id}/movement")
async def api_add_movement(
    shift_id: int,
    req: CashMovementRequest,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.MANAGE_SHIFTS)),
):
    """Registra una entrada o salida de efectivo manual en el turno."""
    return await add_cash_movement(
        session,
        shift_id,
        req.amount,
        req.type,
        req.reason,
        user.id,
        req.category_id
    )

@router.get("/active")
async def api_get_active_shift(
    session: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.TAKE_ORDERS))
):
    """Devuelve el turno actualmente abierto para el usuario logueado."""
    shift = await get_active_shift(session, user_id=user.id)
    if not shift:
        return {"active": False, "shift": None}
    
    # Enriquecemos el turno con datos en tiempo real para el POS
    enriched_shift = await enrich_shift_data(session, shift)
    return {"active": True, "shift": enriched_shift}

@router.get("/active-sessions")
async def api_get_all_active_sessions(
    session: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.MANAGE_SHIFTS)),
):
    """Lista todos los turnos abiertos actualmente en el sistema (Vista Admin)."""
    shifts = await get_all_active_shifts(session)
    return shifts

@router.get("/")
async def api_list_shifts(
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.MANAGE_SHIFTS)),
):
    """Lista todos los turnos históricos con sus totales resumidos."""
    return await list_shifts(session, limit=limit, offset=offset)

@router.get("/{shift_id}/report")
async def api_get_shift_report(
    shift_id: int,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.MANAGE_SHIFTS)),
):
    """Genera un reporte detallado (Z-Cut) de un turno."""
    return await get_shift_report(session, shift_id)
