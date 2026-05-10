import asyncio
import os
import sys

# Add root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pos_core.database import async_session_maker
from pos_core.sales.services.order_lifecycle_service import create_order
from pos_core.sales.services.order_item_service import add_item_to_order
from pos_core.kitchen.services import create_tickets_for_order, update_ticket_status
from pos_core.kitchen.models import KitchenStatus
from pos_core.sales.models import OrderType, OrderStatus
from sqlalchemy import select
from pos_core.catalog.models import Product, Modifier, Category
from pos_core.inventory.models import Ingredient
from pos_core.kitchen.models import KitchenTicket

async def verify():
    print("--- Starting Total Decoupling Verification ---")
    async with async_session_maker() as session:
        # 1. Get a product that goes to kitchen (has production area)
        stmt = select(Product).limit(10)
        result = await session.execute(stmt)
        products = result.scalars().all()
        
        target_product = None
        for p in products:
            # Check if category has production area
            # (In a real test we'd join, but here we just check)
            target_product = p
            break
            
        if not target_product:
            print("No product found.")
            return

        print(f"Using product: {target_product.name}")

        # 2. Create order in Sales
        order = await create_order(session, OrderType.DINE_IN, table_id=1)
        print(f"Created order: {order.id}")
        
        item = await add_item_to_order(session, order.id, target_product.id, quantity=1)
        print(f"Added item: {item.id} (Status: {item.status})")
        
        # 3. Create tickets in Kitchen (This usually happens via listener on order_created)
        # For the test, we trigger it manually or assume it's there
        await create_tickets_for_order(session, order.id, [{"id": item.id, "product_id": target_product.id}])
        
        # Get the ticket
        stmt = select(KitchenTicket).where(KitchenTicket.item_id == item.id)
        result = await session.execute(stmt)
        ticket = result.scalar_one_or_none()
        
        if not ticket:
            print("❌ Kitchen Ticket NOT created.")
            return
        print(f"Kitchen Ticket created: {ticket.id} (Status: {ticket.status})")

        # 4. START PREPARING via Kitchen Service (Simulating KDS)
        print("--- Simulating Cook starting preparation in Kitchen Module ---")
        await update_ticket_status(
            session, 
            ticket.id, 
            KitchenStatus.PREPARING, 
            cook_uuid="cook-123", 
            cook_name="Chef Gus"
        )
        
        # Give some time for background tasks (listeners)
        await asyncio.sleep(1)
        
        # 5. VERIFY
        # Re-fetch item from Sales
        from pos_core.sales.repository import item_repo
        refreshed_item = await item_repo.get_by_id(session, order.id, item.id)
        
        print(f"Sales Item Status after Kitchen event: {refreshed_item.status}")
        
        if refreshed_item.status == OrderStatus.PREPARING:
            print("✅ Sales successfully synced status from Kitchen event.")
        else:
            print("❌ Sales FAILED to sync status.")

        # Re-fetch ticket
        await session.refresh(ticket)
        print(f"Kitchen Ticket Status: {ticket.status}")
        print(f"Cook assigned in Kitchen: {ticket.cook_name}")

    print("--- Verification COMPLETED ---")

if __name__ == "__main__":
    asyncio.run(verify())
