import asyncio
from pos_core.database import get_session
from pos_core.events.service import trigger_broadcast
import logging

logging.basicConfig(level=logging.INFO)

async def test():
    async for db in get_session():
        print("Testing kitchen_orders...")
        await trigger_broadcast("kitchen_orders")
        print("Testing dashboard_stats...")
        await trigger_broadcast("dashboard_stats")
        print("Testing recent_orders...")
        await trigger_broadcast("recent_orders")
        print("Testing tables...")
        await trigger_broadcast("tables")
        break

if __name__ == "__main__":
    asyncio.run(test())
