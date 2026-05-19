from sqlmodel import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any

from ..models import Ingredient, IngredientCreate, IngredientUpdate
from .. import unit_converter
from pos_core.events.service import trigger_broadcast

async def create_ingredient(session: AsyncSession, ingredient: IngredientCreate) -> Ingredient:
    # Asegurar que la unidad base sea la correcta para el tipo de medida si se omite o para validar
    if not ingredient.unit:
        ingredient.unit = unit_converter.get_base_unit(ingredient.measure_type)
        
    db_ingredient = Ingredient.model_validate(ingredient)
    session.add(db_ingredient)
    await session.commit()
    await session.refresh(db_ingredient)
    await trigger_broadcast("inventory")
    return db_ingredient

async def get_ingredients(
    session: AsyncSession, 
    search: Optional[str] = None, 
    category: Optional[str] = None,
    category_ids: Optional[List[int]] = None,
    stock_status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
) -> dict:
    statement = select(Ingredient)
    count_statement = select(func.count(Ingredient.id))
    
    if search:
        # Búsqueda robusta por nombre
        cond = Ingredient.name.ilike(f"%{search}%")
        statement = statement.where(cond)
        count_statement = count_statement.where(cond)
    
    if category_ids:
        cond = Ingredient.category_id.in_(category_ids)
        statement = statement.where(cond)
        count_statement = count_statement.where(cond)
    elif category:
        # Soporte para filtro por nombre de categoría (case-insensitive)
        cond = Ingredient.category.ilike(category)
        statement = statement.where(cond)
        count_statement = count_statement.where(cond)

    # Filtros de Estado de Stock
    if stock_status == "low":
        cond1 = Ingredient.current_stock <= Ingredient.minimum_stock
        cond2 = Ingredient.current_stock > 0
        statement = statement.where(cond1).where(cond2)
        count_statement = count_statement.where(cond1).where(cond2)
    elif stock_status == "none":
        cond = Ingredient.current_stock <= 0
        statement = statement.where(cond)
        count_statement = count_statement.where(cond)
    elif stock_status == "expiring":
        from ..models import IngredientBatch
        from datetime import datetime, timedelta
        # Próximos 7 días
        deadline = datetime.utcnow() + timedelta(days=7)
        subq = select(IngredientBatch.ingredient_id).where(
            IngredientBatch.expiration_date <= deadline,
            IngredientBatch.current_quantity > 0
        )
        cond = Ingredient.id.in_(subq)
        statement = statement.where(cond)
        count_statement = count_statement.where(cond)
    
    # Obtener el conteo total utilizando la consulta optimizada
    total_result = await session.execute(count_statement)
    total = total_result.scalar() or 0
    
    # Aplicar paginación a la consulta de items
    statement = statement.limit(limit).offset(offset)
    result = await session.execute(statement)
    items = result.scalars().all()
    
    return {
        "items": items,
        "total": total,
        "page": (offset // limit) + 1 if limit > 0 else 1,
        "pages": (total + limit - 1) // limit if limit > 0 else 1
    }

async def update_ingredient(session: AsyncSession, ingredient_id: int, ingredient_data: IngredientUpdate) -> Optional[Ingredient]:
    db_ingredient = await session.get(Ingredient, ingredient_id)
    if not db_ingredient:
        return None
    
    update_data = ingredient_data.model_dump(exclude_unset=True)
    
    # Conversión automática de stock si cambia la unidad y no se provee un nuevo stock
    new_unit = update_data.get("unit")
    if new_unit and new_unit != db_ingredient.unit:
        if "current_stock" not in update_data:
            db_ingredient.current_stock = unit_converter.convert_units(
                db_ingredient.current_stock, 
                db_ingredient.unit, 
                new_unit, 
                db_ingredient.measure_type
            )
        if "minimum_stock" not in update_data:
            db_ingredient.minimum_stock = unit_converter.convert_units(
                db_ingredient.minimum_stock, 
                db_ingredient.unit, 
                new_unit, 
                db_ingredient.measure_type
            )

    for key, value in update_data.items():
        setattr(db_ingredient, key, value)
        
    session.add(db_ingredient)
    await session.commit()
    await session.refresh(db_ingredient)
    await trigger_broadcast("inventory")
    return db_ingredient

async def delete_ingredient(session: AsyncSession, ingredient_id: int) -> bool:
    db_ingredient = await session.get(Ingredient, ingredient_id)
    if not db_ingredient:
        return False
    await session.delete(db_ingredient)
    await session.commit()
    await trigger_broadcast("inventory")
    return True
