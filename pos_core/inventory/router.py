from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from pos_core.database import get_session
from .models import (
    Ingredient, IngredientCreate, IngredientUpdate,
    InventoryAdjustment, InventoryAdjustmentCreate, AdjustmentReason,
    IngredientPaginated, InventoryCategory, InventoryCategoryCreate, InventoryCategoryUpdate
)
from .services import ingredient_service, adjustment_service, category_service
from pos_core.auth.dependencies import require_role, get_current_active_user
from pos_core.auth.models import User

router = APIRouter()

# --- Endpoints de Ingredientes ---

@router.get("/ingredients", response_model=IngredientPaginated)
async def list_ingredients(
    search: Optional[str] = None,
    category: Optional[str] = None,
    category_id: Optional[List[int]] = Query(None),
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_session)
):
    """Listado de materia prima en el almacén con filtros y paginación."""
    return await ingredient_service.get_ingredients(
        db, search=search, category=category, category_ids=category_id, limit=limit, offset=offset
    )

@router.post("/ingredients", response_model=Ingredient, dependencies=[Depends(require_role("admin"))])
async def create_ingredient(ingredient: IngredientCreate, db: AsyncSession = Depends(get_session)):
    """Añade un nuevo ingrediente al almacén."""
    return await ingredient_service.create_ingredient(db, ingredient)

@router.put("/ingredients/{ingredient_id}", response_model=Ingredient, dependencies=[Depends(require_role("admin"))])
async def update_ingredient(ingredient_id: int, ingredient: IngredientUpdate, db: AsyncSession = Depends(get_session)):
    """Actualiza un ingrediente existente. Requiere rol: admin."""
    updated_ingredient = await ingredient_service.update_ingredient(db, ingredient_id, ingredient)
    if not updated_ingredient:
        raise HTTPException(status_code=404, detail="Ingrediente no encontrado")
    return updated_ingredient

@router.delete("/ingredients/{ingredient_id}", dependencies=[Depends(require_role("admin"))])
async def delete_ingredient(ingredient_id: int, db: AsyncSession = Depends(get_session)):
    """Elimina un ingrediente. Requiere rol: admin."""
    success = await ingredient_service.delete_ingredient(db, ingredient_id)
    if not success:
        raise HTTPException(status_code=404, detail="Ingrediente no encontrado")
    return {"detail": "Ingrediente eliminado"}

# --- Endpoints de Ajustes / Merma ---

@router.get("/adjustments", response_model=List[InventoryAdjustment], dependencies=[Depends(require_role("admin"))])
async def list_adjustments(
    ingredient_id: Optional[int] = None,
    limit: int = 100, 
    db: AsyncSession = Depends(get_session)
):
    """Historial de mermas y ajustes de inventario. Requiere rol: admin."""
    return await adjustment_service.get_adjustments(db, ingredient_id=ingredient_id, limit=limit)

@router.post("/adjustments", response_model=InventoryAdjustment)
async def create_adjustment(
    adjustment: InventoryAdjustmentCreate, 
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_session)
):
    """
    Registra una merma o ajuste manual.
    Requiere rol: admin o manager.
    """
    user_role = user.custom_metadata.get("role", "waiter")
    if user_role not in ["admin", "manager"]:
         raise HTTPException(
             status_code=403, 
             detail="Permisos insuficientes para registrar movimiento. Se requiere rol admin o manager."
         )

    return await adjustment_service.create_adjustment(
        db, 
        adjustment, 
        actor_uuid=str(user.id), 
        actor_name=getattr(user, "email", "unknown")
    )

# --- Endpoints de Categorías de Inventario ---

@router.get("/categories", response_model=List[InventoryCategory])
async def list_categories(db: AsyncSession = Depends(get_session)):
    """Lista todas las categorías de inventario."""
    return await category_service.get_categories(db)

@router.post("/categories", response_model=InventoryCategory, dependencies=[Depends(require_role("admin"))])
async def create_category(category: InventoryCategoryCreate, db: AsyncSession = Depends(get_session)):
    """Crea una nueva categoría de inventario."""
    return await category_service.create_category(db, category)

@router.put("/categories/{category_id}", response_model=InventoryCategory, dependencies=[Depends(require_role("admin"))])
async def update_category(category_id: int, category: InventoryCategoryUpdate, db: AsyncSession = Depends(get_session)):
    """Actualiza una categoría de inventario."""
    updated = await category_service.update_category(db, category_id, category)
    if not updated:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return updated

@router.delete("/categories/{category_id}", dependencies=[Depends(require_role("admin"))])
async def delete_category(category_id: int, db: AsyncSession = Depends(get_session)):
    """Elimina una categoría de inventario."""
    success = await category_service.delete_category(db, category_id)
    if not success:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return {"detail": "Categoría eliminada"}
