import asyncio
from pos_core.database import get_session
from pos_core.sales.service import get_orders_json
import logging

logging.basicConfig(level=logging.INFO)

async def test():
    async for db in get_session():
        try:
            print("Calling get_orders_json...")
            orders = await get_orders_json(db)
            print(f"Success! Found {len(orders)} orders.")
        except Exception as e:
            print(f"FAILED: {e}")
            import traceback
            traceback.print_exc()
        break

if __name__ == "__main__":
    asyncio.run(test())
