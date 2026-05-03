import asyncio
from sqlmodel import select, func
from pos_core.database import async_session_maker
from pos_core.inventory.models import Product

async def count_products():
    async with async_session_maker() as session:
        count = (await session.execute(select(func.count(Product.id)))).scalar()
        print(f"Total products: {count}")
        
        products = (await session.execute(select(Product))).scalars().all()
        for p in products:
            print(f"- {p.name} (Active: {p.is_active})")

if __name__ == "__main__":
    asyncio.run(count_products())
