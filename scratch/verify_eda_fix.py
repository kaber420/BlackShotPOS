import asyncio
import os
import sys

# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pos_core.database import async_session_maker
from pos_core.sales.services.order_lifecycle_service import create_order, update_order_status
from pos_core.sales.services.order_item_service import add_item_to_order, update_order_item_status
from pos_core.sales.models import OrderType, OrderStatus
from sqlalchemy import select
from pos_core.catalog.models import Category, Product, RecipeItem, Measure, ProductVariant, Modifier, ModifierGroup
from pos_core.kitchen.models import KitchenTicket, ProductionArea
from pos_core.inventory.models import Ingredient
from pos_core.tables.models import Table
from pos_core.sales.models import Order, OrderItem, Payment

async def verify():
    print("--- Starting Verification ---")
    async with async_session_maker() as session:
        # 1. Get a product
        result = await session.execute(select(Product).limit(1))
        product = result.scalars().first()
        if not product:
            print("No product found. Please run seed_data.py first.")
            return

        # 2. Create an order
        order = await create_order(session, OrderType.DINE_IN, table_id=1)
        print(f"Created order: {order.id}")
        
        # 3. Add item
        item = await add_item_to_order(
            session,
            order.id,
            product.id,
            quantity=1
        )
        print(f"Added item: {item.id}")
        
        # 4. Update item status (Test for TypeError fix)
        print(f"Updating item {item.id} status to PREPARING...")
        try:
            # We simulate the router call by passing actor info
            updated_item = await update_order_item_status(
                session,
                order.id,
                item.id,
                OrderStatus.PREPARING,
                actor_uuid="test-uuid",
                actor_name="test-user"
            )
            print(f"✅ Successfully updated item status: {updated_item.status}")
        except TypeError as e:
            print(f"❌ FAILED with TypeError (Signature mismatch): {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ FAILED with error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

        # 5. Update order status (Test for TypeError fix)
        print(f"Updating order {order.id} status to READY...")
        try:
            updated_order = await update_order_status(
                session,
                order.id,
                OrderStatus.READY,
                actor_uuid="test-uuid",
                actor_name="test-user"
            )
            print(f"✅ Successfully updated order status: {updated_order.status}")
        except TypeError as e:
            print(f"❌ FAILED with TypeError (Signature mismatch): {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ FAILED with error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    print("--- Verification COMPLETED ---")

if __name__ == "__main__":
    asyncio.run(verify())
