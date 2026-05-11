import asyncio
from sqlalchemy import text
from pos_core.database import engine

async def migrate():
    print("🚀 Iniciando migración: Agregando menu_background_url a BusinessSettings...")
    
    async with engine.begin() as conn:
        try:
            # SQLModel suele crear la tabla como 'businesssettings'
            # Usamos SQL estándar que funciona en Postgres y SQLite (con precaución)
            # En Postgres, podemos usar 'IF NOT EXISTS' si es una versión reciente
            # Para mayor compatibilidad, intentamos y capturamos el error si ya existe
            await conn.execute(text("ALTER TABLE businesssettings ADD COLUMN menu_background_url TEXT"))
            print("✅ Columna 'menu_background_url' agregada correctamente.")
            print("🎉 Migración completada con éxito.")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("ℹ️  La columna 'menu_background_url' ya existe — no se requiere acción.")
            else:
                print(f"❌ Error durante la migración: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
