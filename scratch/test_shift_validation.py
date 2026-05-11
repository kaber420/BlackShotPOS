
import asyncio
from pos_core.database import async_session_maker
from pos_core.sales.services.order_item_service import add_item_to_order
from pos_core.exceptions import InvalidOrderStateError

async def test_validation():
    async with async_session_maker() as session:
        try:
            # Intentar añadir item sin turno abierto (asumimos que no hay uno)
            await add_item_to_order(session, order_id=1, product_id=1, quantity=1)
            print("FAILED: Item added without shift!")
        except InvalidOrderStateError as e:
            print(f"SUCCESS: Caught expected error: {e}")
        except Exception as e:
            print(f"ERROR: Unexpected exception: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_validation())
