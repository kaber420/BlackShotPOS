import asyncio
import sys
import os
from sqlmodel import SQLModel, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from pos_core.inventory.models import Ingredient, IngredientBatch
from pos_core.auth.models import User
from pos_core.catalog.models import Category, Product, RecipeItem, Measure, ProductVariant
from pos_core.tables.models import Table
from pos_core.accounting.models import Shift, CashRegister, CashMovement
from pos_core.audit.models import AuditLog
from pos_core.settings.models import BusinessSettings
from pos_core.iot.models import IoTDevice
from pos_core.customers.models import Customer
from bs_sync.models import SyncEvent
from pos_core.inventory.services.stock_service import _subtract_from_batches, process_inventory_depletion

# Mocking OrderItem to simulate sales
class MockOrderItem:
    def __init__(self, product_id, variant_id, quantity):
        self.product_id = product_id
        self.product_variant_id = variant_id
        self.quantity = quantity
        self.modifiers = []

async def run_concurrent_sale(engine, async_session_maker, ingredient_id, variant_id, quantity):
    async with async_session_maker() as session:
        item = MockOrderItem(None, variant_id, 1)
        # process_inventory_depletion uses session.commit() inside, but we want to see if locking works
        await process_inventory_depletion(session, [item])

async def stress_test_locking():
    print("\n--- STRESS TEST: Concurrent Sales Locking ---")
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=True)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        
    async with async_session_maker() as session:
        # 1. Setup Data: 1000ml of Milk
        leche = Ingredient(name="Leche", unit="ml", current_stock=1000.0, minimum_stock=10.0)
        session.add(leche)
        await session.commit()
        await session.refresh(leche)
        
        # Batch of 1000ml
        batch = IngredientBatch(ingredient_id=leche.id, original_quantity=1000.0, current_quantity=1000.0)
        session.add(batch)
        
        # Measure
        measure = Measure(name="Unico", value=1.0, unit="pz")
        session.add(measure)
        await session.commit()
        await session.refresh(measure)
        
        # Product Variant that uses 10ml
        product = Product(name="Cafe", price=10.0)
        session.add(product)
        await session.commit()
        await session.refresh(product)
        
        variant = ProductVariant(product_id=product.id, measure_id=measure.id, price=15.0)
        session.add(variant)
        await session.commit()
        await session.refresh(variant)
        
        recipe = RecipeItem(variant_id=variant.id, ingredient_id=leche.id, quantity=10.0)
        session.add(recipe)
        await session.commit()
        
        ingredient_id = leche.id
        variant_id = variant.id

    # 2. Simulate 50 concurrent sales (each taking 10ml)
    # Total expected reduction: 50 * 10 = 500ml
    # Expected final stock: 500ml
    num_concurrent = 50
    print(f"Lanzando {num_concurrent} ventas concurrentes...")
    
    tasks = [run_concurrent_sale(engine, async_session_maker, ingredient_id, variant_id, 1) for _ in range(num_concurrent)]
    await asyncio.gather(*tasks)
    
    # 3. Verify Final Stock
    async with async_session_maker() as session:
        leche_final = await session.get(Ingredient, ingredient_id)
        res = await session.execute(select(IngredientBatch).where(IngredientBatch.ingredient_id == ingredient_id))
        batches = res.scalars().all()
        total_in_batches = sum(b.current_quantity for b in batches)
        
        print(f"Stock inicial: 1000.0ml")
        print(f"Ventas realizadas: {num_concurrent}")
        print(f"Reducción esperada: {num_concurrent * 10.0}ml")
        print(f"Stock final real: {leche_final.current_stock}ml")
        print(f"Total en lotes: {total_in_batches}ml")
        
        if leche_final.current_stock == 500.0 and total_in_batches == 500.0:
            print("✅ STRESS TEST PASSED: El bloqueo pesimista funcionó perfectamente.")
        else:
            print(f"❌ STRESS TEST FAILED: Discrepancia detectada. Stock final: {leche_final.current_stock}ml")

if __name__ == "__main__":
    asyncio.run(stress_test_locking())
