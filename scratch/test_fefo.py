import asyncio
import sys
import os
from sqlmodel import SQLModel, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.getcwd())

from pos_core.inventory.models import Ingredient, IngredientBatch, AdjustmentReason, InventoryAdjustment, InventoryAdjustmentCreate
from pos_core.auth.models import User
from pos_core.catalog.models import Category, Product, RecipeItem, Measure, ProductVariant
from pos_core.tables.models import Table
from pos_core.accounting.models import Shift, CashRegister, CashMovement
from pos_core.audit.models import AuditLog
from pos_core.settings.models import BusinessSettings
from pos_core.iot.models import IoTDevice
from pos_core.customers.models import Customer
from bs_sync.models import SyncEvent
from pos_core.inventory.services.stock_service import _subtract_from_batches
from pos_core.inventory.services.adjustment_service import create_adjustment

async def setup_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    return engine, async_session

async def test_multi_batch_depletion():
    print("\n--- Testing Multi-Batch Depletion (FEFO) ---")
    engine, async_session = await setup_db()
    async with async_session() as session:
        # 1. Setup Data: Ingrediente con 3 lotes
        cafe = Ingredient(name="Cafe", unit="g", current_stock=300.0, minimum_stock=50.0)
        session.add(cafe)
        await session.commit()
        await session.refresh(cafe)
        
        # Lote 1: Caduca mañana (100g)
        b1 = IngredientBatch(
            ingredient_id=cafe.id, 
            original_quantity=100.0, 
            current_quantity=100.0, 
            expiration_date=datetime.utcnow() + timedelta(days=1),
            arrival_date=datetime.utcnow() - timedelta(days=5)
        )
        # Lote 2: Caduca en 5 días (100g)
        b2 = IngredientBatch(
            ingredient_id=cafe.id, 
            original_quantity=100.0, 
            current_quantity=100.0, 
            expiration_date=datetime.utcnow() + timedelta(days=5),
            arrival_date=datetime.utcnow() - timedelta(days=3)
        )
        # Lote 3: Sin caducidad (100g)
        b3 = IngredientBatch(
            ingredient_id=cafe.id, 
            original_quantity=100.0, 
            current_quantity=100.0, 
            expiration_date=None,
            arrival_date=datetime.utcnow() - timedelta(days=1)
        )
        session.add_all([b1, b2, b3])
        await session.commit()
        
        # 2. Descontar 150g (Debe agotar Lote 1 y quitar 50g de Lote 2)
        print("Descontando 150g...")
        await _subtract_from_batches(session, cafe.id, 150.0)
        await session.commit()
        
        # 3. Verificar
        res = await session.execute(select(IngredientBatch).where(IngredientBatch.ingredient_id == cafe.id).order_by(IngredientBatch.expiration_date.asc().nullslast()))
        batches = res.scalars().all()
        
        for i, b in enumerate(batches):
            print(f"Lote {i+1} ({'Sin caducidad' if not b.expiration_date else 'Caduca ' + str(b.expiration_date.date())}): {b.current_quantity}g")
            
        if batches[0].current_quantity == 0.0 and batches[1].current_quantity == 50.0 and batches[2].current_quantity == 100.0:
            print("✅ TEST PASSED: Lotes descontados correctamente siguiendo FEFO.")
        else:
            print("❌ TEST FAILED: Discrepancia en el descuento de lotes.")

async def test_adjustment_reconciliation():
    print("\n--- Testing Adjustment Reconciliation ---")
    engine, async_session = await setup_db()
    async with async_session() as session:
        # 1. Setup Data: Ingrediente con stock 100g y un lote de 100g
        azucar = Ingredient(name="Azucar", unit="g", current_stock=100.0, minimum_stock=10.0)
        session.add(azucar)
        await session.commit()
        await session.refresh(azucar)
        
        b1 = IngredientBatch(ingredient_id=azucar.id, original_quantity=100.0, current_quantity=100.0)
        session.add(b1)
        await session.commit()
        
        # 2. Registrar SALIDA (Merma) de 30g
        print("Registrando salida de 30g...")
        adj_out = InventoryAdjustmentCreate(
            ingredient_id=azucar.id,
            quantity=30.0,
            reason=AdjustmentReason.WASTE,
            note="Azucar derramada"
        )
        await create_adjustment(session, adj_out)
        
        # 3. Verificar stock y lotes
        await session.refresh(azucar)
        res = await session.execute(select(IngredientBatch).where(IngredientBatch.ingredient_id == azucar.id))
        b_after = res.scalar_one()
        
        print(f"Stock actual: {azucar.current_stock}g")
        print(f"Stock en lote: {b_after.current_quantity}g")
        
        if azucar.current_stock == 70.0 and b_after.current_quantity == 70.0:
            print("✅ TEST PASSED: Paridad mantenida tras salida.")
        else:
            print("❌ TEST FAILED: Paridad rota.")

if __name__ == "__main__":
    async def run():
        await test_multi_batch_depletion()
        await test_adjustment_reconciliation()
    asyncio.run(run())
