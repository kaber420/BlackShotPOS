import asyncio
from pos_core.database import get_session
from pos_core.catalog.services.category_service import get_categories

async def main():
    async for session in get_session():
        res = await get_categories(session)
        print("Success:", len(res))
        break

asyncio.run(main())
