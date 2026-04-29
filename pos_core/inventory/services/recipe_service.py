from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ..models import RecipeItem

async def add_ingredient_to_product(session: AsyncSession, recipe_item: RecipeItem) -> RecipeItem:
    """Asocia un ingrediente a un producto con una cantidad específica."""
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
