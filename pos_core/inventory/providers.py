from sqlalchemy.ext.asyncio import AsyncSession
from pos_core.inventory.services.ingredient_service import get_ingredients

from pos_core.events import topic_provider

@topic_provider("inventory")
async def provide_inventory(db: AsyncSession):
    """Proveedor para el tópico 'inventory'."""
    ingredients = await get_ingredients(db)
    return [i.model_dump(mode="json") for i in ingredients]
