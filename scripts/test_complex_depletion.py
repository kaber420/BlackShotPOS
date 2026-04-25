import asyncio
from sqlmodel import SQLModel, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from pos_core.inventory.models import Category, Product, Ingredient, RecipeItem, Measure, ProductVariant, Modifier, ModifierQuantity, ModifierGroup
from pos_core.sales.models import Order, OrderItem, Payment
from pos_core.tables.models import Table
from pos_core.inventory.service import process_inventory_depletion

async def test_inventory_logic():
    # Setup in-memory DB for testing
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with async_session() as session:
        # 1. Setup Data
        measure = Measure(name="Chico", value=1.0, unit="unit")
        session.add(measure)
        await session.commit()
        await session.refresh(measure)

        leche = Ingredient(name="Leche", unit="ml", current_stock=1000.0, minimum_stock=100.0)
        session.add(leche)
        await session.commit()
        await session.refresh(leche)

        product = Product(name="Café", price=30.0, is_active=True, stock=100)
        session.add(product)
        await session.commit()
        await session.refresh(product)

        variant = ProductVariant(product_id=product.id, measure_id=measure.id, price=35.0)
        session.add(variant)
        await session.commit()
        await session.refresh(variant)

        # Receta de la variante: 150ml de leche
        recipe_item = RecipeItem(variant_id=variant.id, ingredient_id=leche.id, quantity=150.0)
        session.add(recipe_item)
        
        # Grupo de Modificadores
        mod_group = ModifierGroup(name="Leches", max_selection=1)
        session.add(mod_group)
        await session.commit()
        await session.refresh(mod_group)

        # Modificador: Extra Leche
        modifier = Modifier(name="Extra Leche", extra_price=5.0, modifier_group_id=mod_group.id, ingredient_id=leche.id, quantity=0.0)
        session.add(modifier)
        await session.commit()
        await session.refresh(modifier)

        # Cantidad específica del modificador para tamaño "Chico": 50ml
        mod_qty = ModifierQuantity(modifier_id=modifier.id, measure_id=measure.id, quantity=50.0)
        session.add(mod_qty)
        await session.commit()

        # 2. Simulate Order Item
        # El POS debe enviar product_variant_id
        item = OrderItem(
            product_id=product.id,
            product_variant_id=variant.id,
            quantity=1,
            unit_price=40.0
        )
        # Mocking modifiers attribute as expected by process_inventory_depletion
        item.modifiers = [modifier]

        # 3. Run Depletion
        print(f"Stock inicial: {leche.current_stock}ml")
        await process_inventory_depletion(session, [item])
        
        await session.refresh(leche)
        print(f"Stock final: {leche.current_stock}ml")

        # 4. Verify
        # Expected: 1000 - 150 (recipe) - 50 (modifier for Chico) = 800
        expected_stock = 800.0
        if leche.current_stock == expected_stock:
            print("✅ TEST PASSED: Depleción calculada correctamente (150 receta + 50 modificador)")
        else:
            print(f"❌ TEST FAILED: Stock esperado {expected_stock}, obtenido {leche.current_stock}")

if __name__ == "__main__":
    asyncio.run(test_inventory_logic())
