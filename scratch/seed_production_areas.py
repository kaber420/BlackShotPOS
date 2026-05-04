import asyncio
import os
import sys
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

# Añadir el directorio raíz al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pos_core.database import init_db, async_session_maker
from pos_core.catalog.models import Category, ProductionArea

async def seed_production_areas():
    print("--- Sembrando Áreas de Producción ---")
    await init_db()
    
    async with async_session_maker() as session:
        # 1. Crear Áreas de Producción si no existen
        result = await session.execute(select(ProductionArea))
        if result.scalars().first():
            print("Ya existen áreas de producción.")
        else:
            print("Creando Barra y Cocina...")
            area_bar = ProductionArea(name="Barra", description="Estación de bebidas calientes y frías", printer_ip="192.168.1.100")
            area_kitchen = ProductionArea(name="Cocina", description="Estación de repostería y alimentos", printer_ip="192.168.1.101")
            session.add_all([area_bar, area_kitchen])
            await session.commit()
            await session.refresh(area_bar)
            await session.refresh(area_kitchen)
            print(f"✅ Áreas creadas: Barra (ID {area_bar.id}), Cocina (ID {area_kitchen.id})")

            # 2. Vincular categorías existentes
            print("Vinculando categorías...")
            # Barra: Café, Té, Bebidas Frías
            statement = select(Category).where(Category.name.in_(["Café", "Té & Infusiones", "Bebidas Frías"]))
            result = await session.execute(statement)
            for cat in result.scalars().all():
                cat.production_area_id = area_bar.id
                session.add(cat)
            
            # Cocina: Repostería
            statement = select(Category).where(Category.name == "Repostería")
            result = await session.execute(statement)
            for cat in result.scalars().all():
                cat.production_area_id = area_kitchen.id
                session.add(cat)
            
            await session.commit()
            print("✅ Categorías vinculadas.")

    print("--- Proceso COMPLETADO ---")

if __name__ == "__main__":
    asyncio.run(seed_production_areas())
