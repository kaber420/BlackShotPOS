from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import List, Optional
from pydantic import BaseModel

from pos_core.database import get_session
from .models import AuditLog, Order, OrderStatus
from omni_auth.security import require_permission
from pos_core.roles import Permission
from pos_core.sales import order_service
from pos_core.events.service import trigger_all_broadcasts
import asyncio

router = APIRouter()

class CancelRequest(BaseModel):
    reason: str

@router.get("/audits", response_model=List[AuditLog])
async def list_audits(
    db: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.VIEW_AUDITS))
):
    """Lista los logs de auditoría más recientes."""
    stmt = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("/orders/{order_id}/cancel")
async def cancel_order_with_reason(
    order_id: int,
    req: CancelRequest,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.MANAGE_KITCHEN_STATUS)),
):
    """
    Cancela una orden completa requiriendo un motivo.
    La lógica de auditoría y liberación de mesa está centralizada en el servicio.
    """
    try:
        order = await order_service.cancel_order(
            db,
            order_id,
            reason=req.reason,
            actor_uuid=user.get("user_uuid"),
            actor_name=user.get("username"),
        )
        
        # Broadcast a las pantallas en tiempo real (KDS y Orders)
        asyncio.create_task(trigger_all_broadcasts())

        return {"status": "success", "order_id": order.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/orders/{order_id}/items/{item_id}/cancel")
async def cancel_item_with_reason(
    order_id: int,
    item_id: int,
    req: CancelRequest,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.MANAGE_KITCHEN_STATUS)),
):
    """
    Cancela un ítem individual requiriendo un motivo.
    """
    try:
        item = await order_service.cancel_order_item(
            db,
            order_id,
            item_id,
            reason=req.reason,
            actor_uuid=user.get("user_uuid"),
            actor_name=user.get("username"),
        )
        
        asyncio.create_task(trigger_all_broadcasts())
        return {"status": "success", "item_id": item.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
