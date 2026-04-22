import asyncio
from pos_core.database import get_session
from pos_core.sales.order_service import get_orders
from pos_core.sales.schemas import OrderRead
import logging

logging.basicConfig(level=logging.INFO)

async def test():
    async for db in get_session():
        try:
            print("Calling get_orders...")
            raw_orders = await get_orders(db)
            orders = [OrderRead.model_validate(o).model_dump(mode="json") for o in raw_orders]
            print(f"Success! Found {len(orders)} orders.")
        except Exception as e:
            print(f"FAILED: {e}")
            import traceback
            traceback.print_exc()
        break

if __name__ == "__main__":
    asyncio.run(test())
