import asyncio
import os
import sys

# Añadir la raíz del proyecto al path para importaciones
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.ext.asyncio import AsyncSession
from pos_core.database import async_session_maker
# Importar todos los modelos para que SQLAlchemy los registre
from pos_core.catalog.models import Category, Product, RecipeItem, Measure, ProductVariant
from pos_core.inventory.models import Ingredient
from pos_core.tables.models import Table
from pos_core.sales.models import Order, OrderItem, Payment, OrderType, OrderStatus, PaymentMethod
from pos_core.accounting.models import Shift
from pos_core.settings.models import BusinessSettings
from pos_core.iot.models import IoTDevice
from pos_core.auth.models import User
from pos_core.customers.models import Customer
from bs_sync.models import SyncEvent

from pos_core.sales import payment_service, order_service
from pos_core.kitchen.models import ProductionArea
from sqlmodel import select

async def test_accounting():
    async with async_session_maker() as session:
        print("\n🧪 Probando Corrección de Ingresos (Revenue Fix)...")
        
        # 1. Crear una categoría y producto de prueba (si no existen)
        from sqlmodel import select
        cat_stmt = select(Category).where(Category.name == "Test Cat")
        cat = (await session.execute(cat_stmt)).scalar_one_or_none()
        if not cat:
            cat = Category(name="Test Cat")
            session.add(cat)
            await session.flush()
        
        prod_stmt = select(Product).where(Product.name == "Café Caro")
        prod = (await session.execute(prod_stmt)).scalar_one_or_none()
        if not prod:
            prod = Product(name="Café Caro", price=80.0, category_id=cat.id)
            session.add(prod)
            await session.flush()
        
        # 1.5 Asegurar Caja, Usuario y Turno Abierto para la Orden
        from pos_core.accounting import service as accounting_service
        from pos_core.accounting.models import CashRegister
        from pos_core.auth.models import User
        from uuid import uuid4
        
        reg_stmt = select(CashRegister).where(CashRegister.name == "Caja Test Fix")
        register = (await session.execute(reg_stmt)).scalar_one_or_none()
        if not register:
            register = CashRegister(name="Caja Test Fix", is_active=True)
            session.add(register)
            await session.flush()
        
        user_stmt = select(User).limit(1)
        user = (await session.execute(user_stmt)).scalar_one_or_none()
        if not user:
            user = User(
                id=uuid4(),
                email="test_fix@blackshot.app",
                username="test_cashier_fix",
                hashed_password="fake",
                is_active=True,
            )
            session.add(user)
            await session.flush()
        
        shift = await accounting_service.open_shift(
            session, 
            initial_cash=500.0, 
            register_id=register.id, 
            user_id=user.id
        )
        print(f"✅ Turno abierto ID: {shift.id}")

        # 2. Crear una orden
        order = await order_service.create_order(session, OrderType.TAKEAWAY)
        print(f"✅ Orden creada ID: {order.id}")
        
        # 3. Añadir ítem de $80
        await order_service.add_item_to_order(session, order.id, prod.id, quantity=1)
        print(f"✅ Ítem añadido: $80.00")
        
        # Recargar con relaciones para evitar error de lazy loading
        from pos_core.sales.repository import order_repo
        order = await order_repo.get_with_relations(session, order.id)
        
        print(f"💰 Total calculado de la orden: ${order.total_price}")
        
        # 4. Pagar con $100 (sobrepago)
        print("💳 Pagando con $100.00...")
        payment = await payment_service.add_payment(
            session, 
            order.id, 
            PaymentMethod.CASH, 
            amount=100.0
        )
        
        # 5. Verificaciones
        print("\n📊 RESULTADOS EN DB:")
        print(f"   - Revenue (amount):   ${payment.amount} (Debe ser 80.0)")
        print(f"   - Recibido:           ${payment.received_amount} (Debe ser 100.0)")
        print(f"   - Cambio:             ${payment.change_amount} (Debe ser 20.0)")
        
        assert payment.amount == 80.0
        assert payment.received_amount == 100.0
        assert payment.change_amount == 20.0
        print("\n✨ ¡PRUEBA EXITOSA! La contaduría cuadra perfectamente.")

if __name__ == "__main__":
    asyncio.run(test_accounting())
