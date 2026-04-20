from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import List, Optional
from pydantic import BaseModel

from pos_core.database import get_session
from .models import AuditLog, AuditAction, Order, OrderStatus
from . import service
from omni_auth.security import require_role
from omni_auth.manager import OmniAuthManager

router = APIRouter()
_auth_manager = OmniAuthManager()

class CancelRequest(BaseModel):
    reason: str

@router.get("/", response_model=List[AuditLog])
async def list_audits(
    db: AsyncSession = Depends(get_session),
    user=Depends(require_role(["admin", "manager"]))
):
    stmt = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("/orders/{order_id}/cancel")
async def cancel_order_with_reason(
    order_id: int,
    req: CancelRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    # Obtain user making request via token
    token = request.headers.get("X-Omni-Token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_info = _auth_manager.verify_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")

    # verify user has permission to manage kitchen status / orders
    perm_dict = user_info.get("permissions", {})
    if not perm_dict.get("can_manage_kitchen_status") and user_info.get("role") not in ["admin", "manager"]:
         raise HTTPException(status_code=403, detail="No tienes permisos para cancelar pedidos. Requiere PIN de administrador.")

    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status == OrderStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Order is already cancelled")

    # Change order status to CANCELLED
    order.status = OrderStatus.CANCELLED
    
    # Store AuditLog
    log = AuditLog(
        action=AuditAction.ORDER_CANCELLED,
        reason=req.reason,
        actor_uuid=user_info.get("uuid", "unknown"),
        actor_name=user_info.get("username", "Unknown User"),
        order_id=order_id
    )

    # Guardar en base de datos
    db.add(log)
    await db.commit()
    await db.refresh(order)

    # Broadcast a las pantallas en tiempo real (KDS y Orders)
    from pos_core.events.service import trigger_all_broadcasts
    import asyncio
    asyncio.create_task(trigger_all_broadcasts())

    return {"status": "success", "order": order.id, "audit_id": log.id}
