from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pydantic import BaseModel

from pos_core.database import get_session
from .shifts_service import open_shift, close_shift, get_active_shift, get_shift_report

router = APIRouter()

class OpenShiftRequest(BaseModel):
    initial_cash: float

class CloseShiftRequest(BaseModel):
    actual_cash: float

@router.post("/open")
async def api_open_shift(req: OpenShiftRequest, session: AsyncSession = Depends(get_session)):
    shift = await open_shift(session, req.initial_cash)
    return shift

@router.post("/{shift_id}/close")
async def api_close_shift(shift_id: int, req: CloseShiftRequest, session: AsyncSession = Depends(get_session)):
    shift = await close_shift(session, shift_id, req.actual_cash)
    return shift

@router.get("/active")
async def api_get_active_shift(session: AsyncSession = Depends(get_session)):
    shift = await get_active_shift(session)
    if not shift:
         return {"active": False, "shift": None}
    return {"active": True, "shift": shift}

@router.get("/{shift_id}/report")
async def api_get_shift_report(shift_id: int, session: AsyncSession = Depends(get_session)):
    report = await get_shift_report(session, shift_id)
    return report
