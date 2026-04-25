import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pos_core.database import async_session_maker
from pos_core.sales.repository import order_repo
from pos_core.sales.schemas import OrderRead

async def validate_all_orders():
    async with async_session_maker() as session:
        orders = await order_repo.get_all(session)
        print(f"Total orders: {len(orders)}")
        for o in orders:
            try:
                OrderRead.model_validate(o)
            except Exception as e:
                print(f"Error validating order {o.id}: {e}")

if __name__ == "__main__":
    asyncio.run(validate_all_orders())
