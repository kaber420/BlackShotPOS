from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no está configurada en el entorno (.env)")

if "postgresql" not in DATABASE_URL:
    raise RuntimeError("Blackshot POS ahora requiere PostgreSQL. Verifica tu DATABASE_URL.")

db_echo_env = os.getenv("DB_ECHO", "False").lower()
is_db_echo = db_echo_env in ("true", "1", "t", "yes")

# Configuración optimizada para PostgreSQL
engine_params = {
    "echo": is_db_echo,
    "pool_size": 20,
    "max_overflow": 10,
    "pool_recycle": 3600,
    "pool_pre_ping": True,
}

engine = create_async_engine(DATABASE_URL, **engine_params)

async_session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def init_db():
    """Inicializa la base de datos creando las tablas si no existen."""
    async with engine.begin() as conn:
        # Importamos los modelos aquí para asegurar que se registren en SQLModel.metadata
        from pos_core.catalog.models import Category, Product, RecipeItem, Measure, ProductVariant
        from pos_core.kitchen.models import KitchenTicket, ProductionArea
        from pos_core.inventory.models import Ingredient
        from pos_core.tables.models import Table, Reservation
        from pos_core.sales.models import Order, OrderItem, Payment
        from pos_core.accounting.models import Shift, CashRegister, CashMovement
        from pos_core.audit.models import AuditLog
        from pos_core.settings.models import BusinessSettings
        from pos_core.iot.models import IoTDevice
        from pos_core.auth.models import User
        from pos_core.customers.models import Customer
        from bs_sync.models import SyncEvent
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_session() -> AsyncSession:
    """Dependency para obtener una sesión de base de datos asíncrona."""
    async with async_session_maker() as session:
        yield session
