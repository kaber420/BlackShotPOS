from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ..models import RecipeItem

from pos_core.inventory.models import Ingredient
from pos_core.inventory import unit_converter
from fastapi import HTTPException

async def add_ingredient_to_product(session: AsyncSession, recipe_item: RecipeItem) -> RecipeItem:
    """Asocia un ingrediente a un producto con una cantidad específica."""
    
    # Handle input conversion if necessary
    final_input_qty = recipe_item.input_quantity if recipe_item.input_quantity is not None else recipe_item.quantity
    final_input_unit = recipe_item.input_unit or ""
    final_quantity = recipe_item.quantity

    if final_input_unit and recipe_item.ingredient_id:
        ingredient = await session.get(Ingredient, recipe_item.ingredient_id)
        if ingredient:
            try:
                final_quantity = unit_converter.convert_units(
                    final_input_qty, 
                    final_input_unit, 
                    ingredient.unit, 
                    ingredient.measure_type
                )
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
                
    recipe_item.quantity = final_quantity
    recipe_item.input_quantity = final_input_qty
    recipe_item.input_unit = final_input_unit

    session.add(recipe_item)
    await session.commit()
    await session.refresh(recipe_item)
    return recipe_item

async def get_product_recipe(session: AsyncSession, product_id: int) -> List[RecipeItem]:
    """Obtiene la lista de ingredientes y cantidades de un producto (base)."""
    statement = select(RecipeItem).where(RecipeItem.product_id == product_id)
    result = await session.execute(statement)
    return result.scalars().all()

async def get_variant_recipe(session: AsyncSession, variant_id: int) -> List[RecipeItem]:
    """Obtiene la lista de ingredientes y cantidades de una variante específica."""
    statement = select(RecipeItem).where(RecipeItem.variant_id == variant_id)
    result = await session.execute(statement)
    return result.scalars().all()
