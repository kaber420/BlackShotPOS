from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from pos_core.database import get_session
from .models import ProductionArea, ProductionAreaCreate, ProductionAreaUpdate, ProductionAreaRead
from pos_core.auth.dependencies import require_role

router = APIRouter()

@router.post("/", response_model=ProductionAreaRead)
async def create_production_area(
    area_in: ProductionAreaCreate,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_role("admin"))
):
    """Crea una nueva área de producción (estación de impresión)."""
    area = ProductionArea.model_validate(area_in)
    session.add(area)
    await session.commit()
    await session.refresh(area)
    return area

@router.get("/", response_model=List[ProductionAreaRead])
async def list_production_areas(
    session: AsyncSession = Depends(get_session),
    user=Depends(require_role("admin"))
):
    """Lista todas las áreas de producción configuradas."""
    statement = select(ProductionArea)
    result = await session.execute(statement)
    return result.scalars().all()

@router.get("/{area_id}", response_model=ProductionAreaRead)
async def get_production_area(
    area_id: int,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_role("admin"))
):
    """Obtiene detalles de un área de producción específica."""
    area = await session.get(ProductionArea, area_id)
    if not area:
        raise HTTPException(status_code=404, detail="Área de producción no encontrada")
    return area

@router.put("/{area_id}", response_model=ProductionAreaRead)
async def update_production_area(
    area_id: int,
    area_in: ProductionAreaUpdate,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_role("admin"))
):
    """Actualiza la configuración de un área de producción."""
    area = await session.get(ProductionArea, area_id)
    if not area:
        raise HTTPException(status_code=404, detail="Área de producción no encontrada")
    
    update_data = area_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(area, key, value)
    
    session.add(area)
    await session.commit()
    await session.refresh(area)
    return area

@router.delete("/{area_id}")
async def delete_production_area(
    area_id: int,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_role("admin"))
):
    """Elimina un área de producción."""
    area = await session.get(ProductionArea, area_id)
    if not area:
        raise HTTPException(status_code=404, detail="Área de producción no encontrada")
    
    await session.delete(area)
    await session.commit()
    return {"status": "ok", "message": "Área de producción eliminada"}
