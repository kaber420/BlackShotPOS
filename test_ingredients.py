import asyncio
from pos_core.database import get_session
from pos_core.inventory.services.ingredient_service import get_ingredients

async def main():
    async for session in get_session():
        res = await get_ingredients(session)
        print("Success ingredients:", len(res))
        break

asyncio.run(main())
