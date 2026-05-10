import asyncio
from sqlalchemy import text
from pos_core.database import engine

async def migrate():
    print("🚀 Iniciando migración: Agregando metadatos de orden a KitchenTicket...")
    
    async with engine.begin() as conn:
        try:
            # 1. Agregar table_id
            await conn.execute(text("ALTER TABLE kitchenticket ADD COLUMN IF NOT EXISTS table_id INTEGER"))
            print("✅ Columna 'table_id' agregada.")
            
            # 2. Agregar order_type
            await conn.execute(text("ALTER TABLE kitchenticket ADD COLUMN IF NOT EXISTS order_type TEXT DEFAULT 'DINE_IN'"))
            print("✅ Columna 'order_type' agregada.")
            
            # 3. Agregar waiter_name
            await conn.execute(text("ALTER TABLE kitchenticket ADD COLUMN IF NOT EXISTS waiter_name TEXT"))
            print("✅ Columna 'waiter_name' agregada.")
            
            # 4. Agregar external_reference
            await conn.execute(text("ALTER TABLE kitchenticket ADD COLUMN IF NOT EXISTS external_reference TEXT"))
            print("✅ Columna 'external_reference' agregada.")
            
            print("🎉 Migración completada con éxito.")
        except Exception as e:
            print(f"❌ Error durante la migración: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
