import asyncio
import os
import sys
from sqlalchemy import text

# Añadir el directorio raíz al path para poder importar pos_core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pos_core.database import engine

async def migrate():
    print("🚀 Iniciando migración: Añadir requires_preparation a la tabla product...")
    
    async with engine.begin() as conn:
        try:
            # PostgreSQL syntax
            await conn.execute(text("ALTER TABLE product ADD COLUMN requires_preparation BOOLEAN DEFAULT TRUE"))
            print("✅ Columna 'requires_preparation' añadida correctamente.")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("ℹ️ La columna 'requires_preparation' ya existe. Saltando.")
            else:
                print(f"❌ Error durante la migración: {e}")
                raise

if __name__ == "__main__":
    asyncio.run(migrate())
