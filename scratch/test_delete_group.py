import asyncio
import os
import sys

# Añadir el directorio raíz al path para poder importar pos_core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pos_core.database import async_session_maker
from pos_core.catalog.models import ModifierGroup, Modifier
from sqlmodel import select

async def test_delete():
    async with async_session_maker() as session:
        # 1. Crear un grupo de prueba
        group = ModifierGroup(name="Test Delete Group")
        session.add(group)
        await session.commit()
        await session.refresh(group)
        print(f"Created group with ID: {group.id}")

        # 2. Intentar borrarlo
        try:
            print(f"Attempting to delete group {group.id}...")
            await session.delete(group)
            await session.commit()
            print("Successfully deleted group!")
        except Exception as e:
            print(f"FAILED to delete group: {e}")
            await session.rollback()

        # 3. Ahora probar con uno que tenga modificadores
        group2 = ModifierGroup(name="Test Delete Group with Modifiers")
        session.add(group2)
        await session.commit()
        await session.refresh(group2)
        
        mod = Modifier(name="Test Mod", modifier_group_id=group2.id, quantity=1)
        session.add(mod)
        await session.commit()
        
        try:
            print(f"Attempting to delete group {group2.id} with modifiers...")
            await session.delete(group2)
            await session.commit()
            print("Successfully deleted group with modifiers!")
        except Exception as e:
            print(f"FAILED to delete group with modifiers: {e}")
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(test_delete())
