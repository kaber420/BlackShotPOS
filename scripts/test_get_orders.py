import asyncio
from pos_core.database import get_session
from pos_core.sales.order_service import get_orders
from pos_core.sales.schemas import OrderRead

async def test():
    async for db in get_session():
        raw_orders = await get_orders(db)
        orders = [OrderRead.model_validate(o).model_dump(mode="json") for o in raw_orders]
        for o in orders:
            if o["id"] == 91:
                print("Order 91 items:", o["items"])
        break

asyncio.run(test())
