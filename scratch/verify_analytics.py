import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from pos_core.analytics.router import get_kitchen_performance, get_waiter_performance, get_dish_speed
from pos_core.database import DATABASE_URL

async def verify_queries():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        print("Checking kitchen performance query...")
        try:
            # We don't execute it, just check if it builds or fails on import/setup
            # Actually, to check the query we might want to run it with explain or just see if it errors
            # Since we might not have data, we just check for obvious SQL errors
            await get_kitchen_performance(db=session, user=None)
            print("✅ Kitchen performance query OK (or failed due to missing auth which is expected)")
        except Exception as e:
            print(f"Kitchen performance: {e}")

        print("Checking waiter performance query...")
        try:
            await get_waiter_performance(db=session, user=None)
            print("✅ Waiter performance query OK")
        except Exception as e:
            print(f"Waiter performance: {e}")

        print("Checking dish speed query...")
        try:
            await get_dish_speed(db=session, user=None)
            print("✅ Dish speed query OK")
        except Exception as e:
            print(f"Dish speed: {e}")

if __name__ == "__main__":
    asyncio.run(verify_queries())
