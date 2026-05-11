
import asyncio
from sqlalchemy import text
from pos_core.database import engine

async def run_migration():
    async with engine.begin() as conn:
        print("🚀 Iniciando migración de categorías de contabilidad...")
        
        # 1. Crear la tabla cashmovementcategory si no existe
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS cashmovementcategory (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) UNIQUE NOT NULL,
                type VARCHAR(50) NOT NULL,
                description TEXT
            )
        """))
        
        # 2. Añadir la columna category_id a cashmovement
        try:
            await conn.execute(text("""
                ALTER TABLE cashmovement ADD COLUMN category_id INTEGER REFERENCES cashmovementcategory(id)
            """))
            print("✅ Columna `category_id` añadida a `cashmovement`.")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("ℹ️ La columna `category_id` ya existe.")
            else:
                print(f"❌ Error al añadir columna: {e}")

        print("✨ Migración completada con éxito.")

if __name__ == "__main__":
    asyncio.run(run_migration())
