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
        
        # Check and add new columns if they do not exist
        try:
            from sqlalchemy import text
            # Check financial_status
            cursor = await conn.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name='order' AND column_name='financial_status';")
            )
            if not cursor.first():
                await conn.execute(text("ALTER TABLE \"order\" ADD COLUMN financial_status VARCHAR(50) DEFAULT 'UNPAID';"))
                
            # Check courtesy_reason
            cursor = await conn.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name='order' AND column_name='courtesy_reason';")
            )
            if not cursor.first():
                await conn.execute(text("ALTER TABLE \"order\" ADD COLUMN courtesy_reason VARCHAR(255);"))
                
            # Check courtesy_by_uuid
            cursor = await conn.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name='order' AND column_name='courtesy_by_uuid';")
            )
            if not cursor.first():
                await conn.execute(text("ALTER TABLE \"order\" ADD COLUMN courtesy_by_uuid VARCHAR(255);"))
                
            # Check cost_per_unit in ingredient
            cursor = await conn.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name='ingredient' AND column_name='cost_per_unit';")
            )
            if not cursor.first():
                await conn.execute(text("ALTER TABLE \"ingredient\" ADD COLUMN cost_per_unit FLOAT DEFAULT 0.0;"))

            # Check username in customer
            cursor = await conn.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name='customer' AND column_name='username';")
            )
            if not cursor.first():
                await conn.execute(text("ALTER TABLE \"customer\" ADD COLUMN username VARCHAR(255) UNIQUE;"))

            # Check hashed_password in customer
            cursor = await conn.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name='customer' AND column_name='hashed_password';")
            )
            if not cursor.first():
                await conn.execute(text("ALTER TABLE \"customer\" ADD COLUMN hashed_password VARCHAR(255);"))
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error en migración automática de base de datos: {e}")


async def get_session() -> AsyncSession:
    """Dependency para obtener una sesión de base de datos asíncrona."""
    async with async_session_maker() as session:
        yield session
