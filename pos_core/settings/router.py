from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pos_core.database import get_session
from .models import BusinessSettings, BusinessSettingsUpdate
from . import service
from omni_auth.security import require_role

router = APIRouter()

@router.get("", response_model=BusinessSettings)
async def get_settings(db: AsyncSession = Depends(get_session)):
    """Obtiene la configuración global del negocio."""
    return await service.get_settings(db)

@router.patch("", response_model=BusinessSettings)
async def update_settings(
    settings_in: BusinessSettingsUpdate,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_role("can_manage_settings")),
):
    """Actualiza la configuración del negocio (requiere permisos de gestión)."""
    return await service.update_settings(db, settings_in)
