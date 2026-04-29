from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

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

async def get_ingredients(session: AsyncSession) -> List[Ingredient]:
    statement = select(Ingredient)
    result = await session.execute(statement)
    return result.scalars().all()

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
