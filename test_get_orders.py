import asyncio
from pos_core.database import get_session
from pos_core.sales.service import get_orders_json

async def test():
    async for db in get_session():
        orders = await get_orders_json(db)
        for o in orders:
            if o["id"] == 91:
                print("Order 91 items:", o["items"])
        break

asyncio.run(test())
