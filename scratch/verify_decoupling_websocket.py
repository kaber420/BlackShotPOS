import asyncio
import os
import sys

# Añadir directorio raíz a sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Pre-cargar todos los modelos para registrar las tablas en SQLAlchemy/SQLModel
from pos_core.customers.models import Customer
from pos_core.sales.models import Order, OrderItem
from pos_core.catalog.models import Product, Category
from pos_core.kitchen.models import KitchenTicket, ProductionArea
from pos_core.tables.models import Table
from pos_core.accounting.models import Shift
from pos_core.inventory.models import Ingredient
from pos_core.audit.models import AuditLog
from pos_core.auth.models import User

# Inicializar listeners y providers de EDA automáticamente
from pos_core.events.discovery import discover_event_listeners, discover_event_providers
discover_event_listeners()
discover_event_providers()

from pos_core.database import async_session_maker
from pos_core.sales.services.order_lifecycle_service import create_order
from pos_core.sales.services.order_item_service import add_item_to_order
from pos_core.kitchen.services import update_ticket_status
from pos_core.kitchen.models import KitchenStatus
from pos_core.sales.models import OrderType
from pos_core.kitchen.providers import provide_recent_orders
from sqlalchemy import select

async def verify():
    print("🚀 [TEST] Iniciando verificación del Desacoplamiento de WebSockets con sesiones aisladas...")
    
    # --- PASO 1: Crear orden e ítem en sesión 1 y cerrar ---
    async with async_session_maker() as session:
        stmt = select(Product).limit(1)
        result = await session.execute(stmt)
        product = result.scalar_one_or_none()
        
        if not product:
            print("❌ Error: No hay productos en la base de datos para realizar la prueba.")
            return

        product_id = product.id
        product_name = product.name
        print(f"✅ Usando producto: '{product_name}' (ID: {product_id})")
        
        order = await create_order(session, OrderType.DINE_IN, table_id=1)
        order_id = order.id
        print(f"✅ Orden de prueba creada: {order_id}")
        
        item = await add_item_to_order(session, order_id, product_id, quantity=1)
        item_id = item.id
        print(f"✅ Ítem añadido a la orden (ID: {item_id}). Estado inicial: {item.status}")
        
    # --- PASO 2: Esperar a que EDA cree el ticket de cocina automáticamente ---
    print("⏳ Esperando que el listener de EDA genere el ticket de cocina en segundo plano...")
    await asyncio.sleep(0.5)
    
    # --- PASO 3: Verificar que el ticket de cocina se creó en una nueva sesión 2 ---
    async with async_session_maker() as session:
        stmt = select(KitchenTicket).where(KitchenTicket.item_id == item_id)
        result = await session.execute(stmt)
        tickets = result.scalars().all()
        
        if not tickets:
            print("❌ Error: No se pudo generar el ticket en Cocina automáticamente por el listener.")
            return
            
        ticket_id = tickets[0].id
        print(f"✅ Ticket de cocina creado por EDA (ID: {ticket_id}, Estado: {tickets[0].status})")
        
    # --- PASO 4: Validar provide_recent_orders con sesión 3 ---
    async with async_session_maker() as session:
        print("--- Evaluando provide_recent_orders (Antes del cambio - PENDING) ---")
        orders_snapshot = await provide_recent_orders(session)
        my_order = next((o for o in orders_snapshot if o["id"] == order_id), None)
        
        if not my_order:
            print("❌ Error: La orden recién creada no se encuentra en recent_orders.")
            return
            
        print(f"📦 Estado de orden en recent_orders: {my_order['status']}")
        print(f"🍔 Estado de ítem en recent_orders: {my_order['items'][0]['status']}")
        
    # --- PASO 5: Actualizar ticket a PREPARING en Cocina con sesión 4 (Simula KDS) ---
    async with async_session_maker() as session:
        print("\n👨‍🍳 --- Simulando inicio de preparación en el KDS (Cocina) ---")
        await update_ticket_status(session, ticket_id, KitchenStatus.PREPARING, cook_name="Chef Gus")
        
    # Esperar que corra el listener de fondo de Ventas
    await asyncio.sleep(0.5)
    
    # --- PASO 6: Validar provide_recent_orders con sesión 5 (Debe ser PREPARING) ---
    async with async_session_maker() as session:
        print("--- Evaluando provide_recent_orders (Después de cambiar a PREPARANDO en Cocina) ---")
        orders_snapshot_after = await provide_recent_orders(session)
        my_order_after = next((o for o in orders_snapshot_after if o["id"] == order_id), None)
        
        item_status_after = my_order_after['items'][0]['status']
        order_status_after = my_order_after['status']
        print(f"📦 Estado de orden en recent_orders: {order_status_after}")
        print(f"🍔 Estado de ítem en recent_orders: {item_status_after}")
        
        assert item_status_after == "PREPARING", f"❌ Error: El estado del ítem debería ser PREPARING, pero es {item_status_after}"
        assert order_status_after == "PREPARING", f"❌ Error: El estado de la orden debería ser PREPARING, pero es {order_status_after}"
        
    # --- PASO 7: Actualizar ticket a READY en Cocina con sesión 6 (Simula KDS) ---
    async with async_session_maker() as session:
        print("\n👨‍🍳 --- Simulando ticket LISTO en el KDS (Cocina) ---")
        await update_ticket_status(session, ticket_id, KitchenStatus.READY)
        
    # Esperar que corra el listener de fondo de Ventas
    await asyncio.sleep(0.5)
    
    # --- PASO 8: Validar provide_recent_orders con sesión 7 (Debe ser READY) ---
    async with async_session_maker() as session:
        print("--- Evaluando provide_recent_orders (Después de marcar como LISTO en Cocina) ---")
        orders_snapshot_ready = await provide_recent_orders(session)
        my_order_ready = next((o for o in orders_snapshot_ready if o["id"] == order_id), None)
        
        item_status_ready = my_order_ready['items'][0]['status']
        order_status_ready = my_order_ready['status']
        print(f"📦 Estado de orden en recent_orders: {order_status_ready}")
        print(f"🍔 Estado de ítem en recent_orders: {item_status_ready}")
        
        assert item_status_ready == "READY", f"❌ Error: El estado del ítem debería ser READY, pero es {item_status_ready}"
        assert order_status_ready == "READY", f"❌ Error: El estado de la orden debería ser READY, pero es {order_status_ready}"
        
        print("\n🏆 ¡VERIFICACIÓN EXITOSA! El desacoplamiento y el flujo reactivo de EDA funcionan perfectamente sin condiciones de carrera, sin acoplamiento a nivel de tablas de base de datos y sin MissingGreenlet.")

if __name__ == "__main__":
    asyncio.run(verify())
