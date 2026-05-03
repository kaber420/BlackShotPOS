import asyncio
from pos_core.database import get_session
from pos_core.catalog.services.product_service import get_products

async def main():
    async for session in get_session():
        res = await get_products(session)
        print("Success products:", len(res))
        break

asyncio.run(main())
