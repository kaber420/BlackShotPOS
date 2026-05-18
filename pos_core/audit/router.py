from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import List, Optional
from pydantic import BaseModel

from pos_core.database import get_session
from .models import AuditLog
from pos_core.auth.dependencies import require_permission
from pos_core.roles import Permission
import asyncio

router = APIRouter()

@router.get("/audits", response_model=List[AuditLog])
async def list_audits(
    db: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.VIEW_AUDITS))
):
    """Lista los logs de auditoría más recientes."""
    stmt = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100)
    res = await db.execute(stmt)
    return res.scalars().all()
