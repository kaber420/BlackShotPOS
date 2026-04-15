from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Por defecto usamos SQLite con aiosqlite para facilidad de inicio
# Se puede cambiar por postgresql+asyncpg://user:pass@host/dbname en .env
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./pos_database.db")

# check_same_thread es necesario solo para SQLite
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

db_echo_env = os.getenv("DB_ECHO", "False").lower()
is_db_echo = db_echo_env in ("true", "1", "t", "yes")

engine = create_async_engine(
    DATABASE_URL, 
    echo=is_db_echo, 
    connect_args=connect_args
)

async_session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def init_db():
    """Inicializa la base de datos creando las tablas si no existen."""
    async with engine.begin() as conn:
        # Importamos los modelos aquí para asegurar que se registren en SQLModel.metadata
        from pos_core.inventory.models import Category, Product, Ingredient, RecipeItem, Measure, ProductVariant
        from pos_core.tables.models import Table
        from pos_core.sales.models import Order, OrderItem, Payment, Shift
        from pos_core.settings.models import BusinessSettings
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_session() -> AsyncSession:
    """Dependency para obtener una sesión de base de datos asíncrona."""
    async with async_session_maker() as session:
        yield session
