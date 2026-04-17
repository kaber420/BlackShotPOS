import asyncio
import os
import sys

# Añadir el directorio raíz al path para poder importar pos_core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from pos_core.database import async_session_maker
from pos_core.inventory.models import Product
from sqlmodel import select

async def main():
    async with async_session_maker() as session:
        statement = select(Product)
        result = await session.execute(statement)
        products = result.scalars().all()
        for p in products:
            print(f"ID={p.id} Name={p.name} ImageUrl={p.image_url}")

if __name__ == "__main__":
    asyncio.run(main())
