import asyncio
import logging
import sys
import os

# Añadir el directorio actual al path
sys.path.append(os.getcwd())

from pos_core.database import init_db, async_session_maker
from pos_core.events.bus import event_bus
from pos_core.events.discovery import discover_event_listeners
from pos_core.kitchen.models import KitchenTicket, KitchenStatus
from pos_core.kitchen.repository import kitchen_repo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_eda")

async def verify():
    logger.info("🚀 Iniciando verificación de EDA...")
    
    # 1. Preparar entorno
    await init_db()
    discover_event_listeners()
    
    async with async_session_maker() as session:
        # 2. Crear ticket de prueba
        ticket = KitchenTicket(
            order_id=999,
            item_id=888,
            product_name="Café Americano",
            table_id=1,
            status=KitchenStatus.PENDING
        )
        session.add(ticket)
        await session.commit()
        await session.refresh(ticket)
        ticket_id = ticket.id
        logger.info(f"✅ Ticket de prueba creado: ID={ticket_id}, Order={ticket.order_id}, Table={ticket.table_id}")

    # 3. Test: Transferencia de mesa
    logger.info("📤 Publicando sales.order_transferred...")
    await event_bus.publish("sales.order_transferred", {
        "order_id": 999,
        "from_table_id": 1,
        "to_table_id": 2
    })
    
    await asyncio.sleep(0.5) # Esperar a que el listener procese
    
    async with async_session_maker() as session:
        ticket = await session.get(KitchenTicket, ticket_id)
        if ticket.table_id == 2:
            logger.info("✅ OK: Mesa actualizada en ticket.")
        else:
            logger.error(f"❌ ERROR: Mesa no actualizada. Valor actual: {ticket.table_id}")

    # 4. Test: Cancelación de item
    logger.info("📤 Publicando sales.item_cancelled...")
    await event_bus.publish("sales.item_cancelled", {
        "order_id": 999,
        "item_id": 888,
        "reason": "Cliente cambió de opinión"
    })
    
    await asyncio.sleep(0.5)
    
    async with async_session_maker() as session:
        ticket = await session.get(KitchenTicket, ticket_id)
        if ticket.status == KitchenStatus.CANCELLED:
            logger.info("✅ OK: Ticket cancelado.")
        else:
            logger.error(f"❌ ERROR: Ticket no cancelado. Estado: {ticket.status}")

    # 5. Test: Split de orden
    # Reset ticket para split
    async with async_session_maker() as session:
        ticket.status = KitchenStatus.PENDING
        session.add(ticket)
        await session.commit()

    logger.info("📤 Publicando sales.order_split...")
    await event_bus.publish("sales.order_split", {
        "original_order_id": 999,
        "new_order_id": 1000,
        "items_split": [{"item_id": 888, "quantity": 1}]
    })
    
    await asyncio.sleep(0.5)
    
    async with async_session_maker() as session:
        ticket = await session.get(KitchenTicket, ticket_id)
        if ticket.order_id == 1000:
            logger.info("✅ OK: Ticket movido a la nueva orden.")
        else:
            logger.error(f"❌ ERROR: Ticket no movido. Order ID: {ticket.order_id}")

    # Limpieza opcional
    async with async_session_maker() as session:
        await session.delete(ticket)
        await session.commit()
    
    logger.info("🏁 Verificación completada.")

if __name__ == "__main__":
    asyncio.run(verify())
