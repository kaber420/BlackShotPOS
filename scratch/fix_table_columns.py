import asyncio
from sqlalchemy import text
from pos_core.database import engine

async def main():
    async with engine.begin() as conn:
        print("Añadiendo columnas faltantes a la tabla 'table'...")
        try:
            await conn.execute(text('ALTER TABLE "table" ADD COLUMN IF NOT EXISTS waiter_requested BOOLEAN DEFAULT FALSE;'))
            await conn.execute(text('ALTER TABLE "table" ADD COLUMN IF NOT EXISTS bill_requested BOOLEAN DEFAULT FALSE;'))
            print("¡Columnas añadidas exitosamente!")
        except Exception as e:
            print(f"Error al modificar la tabla: {e}")

if __name__ == '__main__':
    asyncio.run(main())
