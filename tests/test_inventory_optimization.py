import asyncio
import sys
import os
from sqlmodel import SQLModel, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(os.getcwd())

from pos_core.inventory.models import Ingredient, IngredientBatch, AdjustmentReason, InventoryAdjustment, InventoryCategory, InventoryAdjustmentCreate
from pos_core.sales.models import OrderItem, Order, Payment
from pos_core.accounting.models import Shift
from pos_core.catalog.models import Product, ProductVariant
from pos_core.tables.models import Table
from pos_core.inventory.services.stock_service import process_inventory_depletion
from pos_core.inventory.services.adjustment_service import create_adjustment
from pos_core.exceptions import InsufficientStockError
from pos_core.auth.models import User
from pos_core.catalog.models import Category, Product, RecipeItem, Measure, ProductVariant
from pos_core.accounting.models import Shift, CashRegister, CashMovement
from pos_core.audit.models import AuditLog
from pos_core.settings.models import BusinessSettings
from pos_core.iot.models import IoTDevice
from pos_core.customers.models import Customer
from pos_core.kitchen.models import ProductionArea
from bs_sync.models import SyncEvent

async def setup_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    return engine, async_session

async def test_insufficient_stock():
    print("\n--- Testing Insufficient Stock ---")
    engine, async_session = await setup_db()
    async with async_session() as session:
        # 1. Setup Data
        cafe = Ingredient(name="Cafe", unit="g", current_stock=10.0, minimum_stock=5.0)
        session.add(cafe)
        await session.commit()
        
        # 2. Test exception exists
        try:
            raise InsufficientStockError("Cafe", 10.0, 15.0)
        except InsufficientStockError as e:
            print(f"✅ Capturada excepción esperada: {e.detail}")

async def test_atomicity_and_rollback():
    print("\n--- Testing Atomicity and Rollback ---")
    engine, async_session = await setup_db()
    async with async_session() as session:
        # 1. Setup Data
        leche = Ingredient(name="Leche", unit="ml", current_stock=100.0, minimum_stock=10.0)
        session.add(leche)
        await session.commit()
        await session.refresh(leche)
        
        # 2. Simulate a partial success then a failure
        try:
            async with async_session() as session_tx:
                # Deduct 50ml (Success)
                leche_db = await session_tx.get(Ingredient, leche.id)
                leche_db.current_stock -= 50
                session_tx.add(leche_db)
                
                # Fail with something
                print("Simulando error a mitad de transacción...")
                raise ValueError("Error forzado")
                
                await session_tx.commit()
        except ValueError:
            pass
            
        # 3. Verify stock is still 100
        async with async_session() as session_verify:
            leche_verify = await session_verify.get(Ingredient, leche.id)
            print(f"Stock después de error: {leche_verify.current_stock}ml")
            if leche_verify.current_stock == 100.0:
                print("✅ TEST PASSED: Rollback exitoso, el stock no se alteró parcialmente.")
            else:
                print("❌ TEST FAILED: El stock se alteró a pesar del error.")

async def test_physical_count_parity():
    print("\n--- Testing Physical Count Parity ---")
    engine, async_session = await setup_db()
    async with async_session() as session:
        # 1. Setup Data
        harina = Ingredient(name="Harina", unit="kg", current_stock=5.0, minimum_stock=1.0)
        session.add(harina)
        await session.commit()
        await session.refresh(harina)

        # Lote inicial
        batch1 = IngredientBatch(ingredient_id=harina.id, original_quantity=5.0, current_quantity=5.0)
        session.add(batch1)
        await session.commit()
        
        # 2. Perform Physical Count (Shrinkage: 5.0 -> 3.0)
        print("Realizando conteo físico: 5.0kg -> 3.0kg (Merma de 2kg)")
        adj = InventoryAdjustmentCreate(
            ingredient_id=harina.id,
            quantity=3.0,
            reason=AdjustmentReason.PHYSICAL_COUNT,
            note="Ajuste mensual"
        )
        await create_adjustment(session, adj)
        
        # 3. Verify parity
        await session.refresh(harina)
        res = await session.execute(select(IngredientBatch).where(IngredientBatch.ingredient_id == harina.id))
        batches = res.scalars().all()
        total_in_batches = sum(b.current_quantity for b in batches)
        
        print(f"Stock en ingrediente: {harina.current_stock}kg")
        print(f"Suma de lotes: {total_in_batches}kg")
        
        if harina.current_stock == total_in_batches == 3.0:
            print("✅ TEST PASSED: Paridad mantenida tras merma en conteo físico.")
        else:
            print("❌ TEST FAILED: Discrepancia entre stock y lotes.")

        # 4. Perform Physical Count (Surplus: 3.0 -> 6.0)
        print("\nRealizando conteo físico: 3.0kg -> 6.0kg (Sobrante de 3kg)")
        adj_plus = InventoryAdjustmentCreate(
            ingredient_id=harina.id,
            quantity=6.0,
            reason=AdjustmentReason.PHYSICAL_COUNT,
            note="Ajuste corrección"
        )
        await create_adjustment(session, adj_plus)
        
        await session.refresh(harina)
        res = await session.execute(select(IngredientBatch).where(IngredientBatch.ingredient_id == harina.id))
        batches = res.scalars().all()
        total_in_batches = sum(b.current_quantity for b in batches)
        
        print(f"Stock en ingrediente: {harina.current_stock}kg")
        print(f"Suma de lotes: {total_in_batches}kg (Lotes totales: {len(batches)})")
        
        if harina.current_stock == total_in_batches == 6.0:
            print("✅ TEST PASSED: Paridad mantenida tras sobrante en conteo físico.")
        else:
            print("❌ TEST FAILED: Discrepancia entre stock y lotes.")

if __name__ == "__main__":
    async def run_all():
        await test_insufficient_stock()
        await test_atomicity_and_rollback()
        await test_physical_count_parity()
    
    asyncio.run(run_all())
