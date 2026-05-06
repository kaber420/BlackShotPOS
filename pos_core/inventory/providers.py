from sqlalchemy.ext.asyncio import AsyncSession
from pos_core.inventory.services.ingredient_service import get_ingredients

from pos_core.events import topic_provider

@topic_provider("inventory")
async def provide_inventory(db: AsyncSession):
    """Proveedor para el tópico 'inventory'."""
    # get_ingredients ahora devuelve un dict con paginación
    res = await get_ingredients(db, limit=100) # Devolvemos top 100 para tiempo real
    ingredients = res.get("items", [])
    return [i.model_dump(mode="json") for i in ingredients]
