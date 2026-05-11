import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from dotenv import load_dotenv

# Import all models to ensure they are registered in SQLModel.metadata
from pos_core.catalog.models import Category, Product, RecipeItem, Measure, ProductVariant
from pos_core.kitchen.models import KitchenTicket, ProductionArea
from pos_core.inventory.models import Ingredient
from pos_core.tables.models import Table
from pos_core.sales.models import Order, OrderItem, Payment
from pos_core.accounting.models import Shift, CashRegister, CashMovement
from pos_core.audit.models import AuditLog
from pos_core.settings.models import BusinessSettings
from pos_core.iot.models import IoTDevice
from pos_core.auth.models import User
from pos_core.customers.models import Customer
from bs_sync.models import SyncEvent

dotenv_path = os.path.join("/home/kaberromero/Documentos/proyectos/BlackShotPOS", ".env")
load_dotenv(dotenv_path)
DATABASE_URL = os.getenv("DATABASE_URL")

async def reset_db():
    if not DATABASE_URL:
        print("DATABASE_URL not found in .env")
        return

    print(f"Connecting to {DATABASE_URL}...")
    engine = create_async_engine(DATABASE_URL)

    async with engine.begin() as conn:
        if "postgresql" in DATABASE_URL:
            print("PostgreSQL detected. Using DROP SCHEMA CASCADE...")
            await conn.execute(text("DROP SCHEMA public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
            await conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
            await conn.execute(text("GRANT ALL ON SCHEMA public TO blackshot_user")) # Specific to this project's user
        else:
            print("Dropping all tables...")
            await conn.run_sync(SQLModel.metadata.drop_all)
            
        print("Creating all tables...")
        await conn.run_sync(SQLModel.metadata.create_all)

    await engine.dispose()
    print("Database reset successfully.")

if __name__ == "__main__":
    asyncio.run(reset_db())
