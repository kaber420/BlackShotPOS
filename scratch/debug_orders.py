
import asyncio
from pos_core.database import async_session_maker
from pos_core.sales.models import Order
from sqlalchemy import select

async def debug_orders():
    async with async_session_maker() as session:
        result = await session.execute(select(Order))
        orders = result.scalars().all()
        for o in orders:
            print(f"Order ID: {o.id}, Status: {o.status}, Total: {o.total_amount}, Subtotal: {o.subtotal}")

if __name__ == "__main__":
    asyncio.run(debug_orders())
