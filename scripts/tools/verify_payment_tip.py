import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from pos_core.database import get_session, engine
from pos_core.sales.payment_service import add_payment
from pos_core.sales.models import Order, PaymentMethod, OrderStatus, OrderType
# Import other models to ensure metadata is loaded for foreign keys
from pos_core.tables.models import Table
from pos_core.inventory.models import Product, Category, Ingredient, Modifier, ProductVariant
from pos_core.customers.models import Customer
from sqlmodel import Session, select

async def verify():
    print("Starting verification of payment tip handling...")
    async for session in get_session():
        # 1. Create a dummy order
        order = Order(
            type=OrderType.DINE_IN,
            status=OrderStatus.PENDING,
            total_amount=100.0,
            subtotal=100.0
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)
        print(f"Created order {order.id} with total {order.total_amount}")

        # 2. Add payment with tip and received amount
        # Bill: 100, Tip: 10, Received: 120 (Change should be 10)
        try:
            payment = await add_payment(
                session,
                order.id,
                PaymentMethod.CASH,
                amount=100.0,
                received_amount=120.0,
                tip_amount=10.0
            )
            
            print(f"Payment registered: ID={payment.id}")
            print(f"Amount: {payment.amount}")
            print(f"Tip: {payment.tip_amount}")
            print(f"Received: {payment.received_amount}")
            print(f"Change: {payment.change_amount}")
            
            assert payment.amount == 100.0
            assert payment.tip_amount == 10.0
            assert payment.received_amount == 120.0
            assert payment.change_amount == 10.0
            
            await session.refresh(order)
            print(f"Order status: {order.status}")
            assert order.status == OrderStatus.PAID
            
            print("Verification SUCCESSFUL!")
        except Exception as e:
            print(f"Verification FAILED: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Clean up (optional, but good for repeatability)
            # await session.delete(order)
            # await session.commit()
            pass
        break

if __name__ == "__main__":
    asyncio.run(verify())
