import sys
import os
import asyncio

# Añadir el directorio raíz al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pos_core.database import async_session_maker, init_db
from pos_core.customers.service import CustomerService
from pos_core.customers.schemas import CustomerCreate, CustomerUpdate

async def test_pos_admin_flow():
    print("--- 🧪 Test de Integración: Gestión de Clientes desde el POS ---")
    await init_db()
    
    async with async_session_maker() as session:
        print("\n1. Registrando clientes desde la terminal de caja...")
        c1 = CustomerCreate(
            name="Mateo Martínez",
            username="mateo_cafe",
            password="password123",
            phone="5522334455",
            email="mateo@example.com"
        )
        c2 = CustomerCreate(
            name="Lucía López",
            username="lucia_cafe",
            password="password456",
            phone="5566778899",
            email="lucia@example.com"
        )
        
        # Limpieza previa
        for u in ["mateo_cafe", "lucia_cafe"]:
            existing = await CustomerService.get_by_username(session, u)
            if existing:
                await session.delete(existing)
        await session.commit()
        
        cust1 = await CustomerService.create(session, c1)
        cust2 = await CustomerService.create(session, c2)
        print(f"✅ Clientes creados con éxito: {cust1.name} (@{cust1.username}) y {cust2.name} (@{cust2.username})")
        
        print("\n2. Probando listado general (Fase 1 - POS Admin List)...")
        all_customers = await CustomerService.list_all(session, limit=10)
        usernames = [c.username for c in all_customers if c.username]
        print(f"👥 Clientes encontrados en base local: {len(all_customers)}")
        print(f"   Usuarios con login: {', '.join(usernames)}")
        assert "mateo_cafe" in usernames
        assert "lucia_cafe" in usernames
        print("✅ Método CustomerService.list_all funciona correctamente.")
        
        print("\n3. Actualizando datos financieros y NFC desde el POS...")
        update_payload = CustomerUpdate(
            points=150,
            credit_balance=350.50,
            tier="gold",
            nfc_tag_id="NFC_TAG_MATEO_123"
        )
        updated = await CustomerService.update(session, cust1, update_payload)
        print(f"✅ Datos del cliente '{updated.name}' actualizados:")
        print(f"   Puntos: {updated.points} (Esperado: 150)")
        print(f"   Monedero: ${updated.credit_balance} (Esperado: 350.50)")
        print(f"   Nivel VIP: {updated.tier} (Esperado: gold)")
        print(f"   Tag NFC: {updated.nfc_tag_id} (Esperado: NFC_TAG_MATEO_123)")
        assert updated.points == 150
        assert updated.credit_balance == 350.50
        assert updated.tier == "gold"
        assert updated.nfc_tag_id == "NFC_TAG_MATEO_123"
        
        # Limpieza
        print("\nLimpiando datos de prueba...")
        await session.delete(cust1)
        await session.delete(cust2)
        await session.commit()
        print("✅ Limpieza completada.")

        print("\n4. Probando eliminación segura y desvinculación de referencias...")
        # Crear un cliente nuevo de prueba
        c3 = CustomerCreate(
            name="Sandra Sosa",
            username="sandra_cafe",
            password="password789",
            phone="5511223344",
            email="sandra@example.com"
        )
        # Limpieza previa de Sandra si existe
        existing_sandra = await CustomerService.get_by_username(session, "sandra_cafe")
        if existing_sandra:
            await session.delete(existing_sandra)
            await session.commit()

        cust3 = await CustomerService.create(session, c3)
        print(f"✅ Cliente de prueba creado: {cust3.name} (UUID: {cust3.id})")

        # Crear una orden ficticia vinculada a este cliente
        from pos_core.sales.models import Order, OrderType, OrderStatus, OrderFinancialStatus
        test_order = Order(
            type=OrderType.DINE_IN,
            status=OrderStatus.PAID,
            financial_status=OrderFinancialStatus.PAID,
            subtotal=120.0,
            total_amount=120.0,
            customer_id=cust3.id
        )
        session.add(test_order)

        # Crear una reservación ficticia vinculada a este cliente
        from pos_core.tables.models import Reservation
        from datetime import datetime
        test_reservation = Reservation(
            customer_name=cust3.name,
            customer_phone=c3.phone,
            customer_id=cust3.id,
            reservation_time=datetime.now()
        )
        session.add(test_reservation)
        await session.commit()
        await session.refresh(test_order)
        await session.refresh(test_reservation)
        print(f"✅ Orden de venta y reservación ficticias creadas y vinculadas a {cust3.name}")

        # Ejecutar la eliminación segura
        delete_result = await CustomerService.delete(session, cust3.id)
        assert delete_result is True
        print(f"✅ CustomerService.delete ejecutado con éxito")

        # Validar que el cliente ya no existe en la base de datos
        deleted_cust = await CustomerService.get_by_id(session, cust3.id)
        assert deleted_cust is None
        print(f"✅ Verificado: El cliente fue eliminado físicamente.")

        # Validar que la orden y la reservación permanecen pero con customer_id = None
        await session.refresh(test_order)
        await session.refresh(test_reservation)
        assert test_order.customer_id is None
        assert test_reservation.customer_id is None
        print(f"✅ Verificado: La orden y la reservación fueron desvinculadas de forma limpia (customer_id = None).")

        # Limpiar orden y reservación creadas para el test
        await session.delete(test_order)
        await session.delete(test_reservation)
        await session.commit()
        print("✅ Limpieza de entidades de prueba completada.")

        print("\n🎉 ¡Todas las pruebas de administración de clientes pasaron con éxito! 🎉")

if __name__ == "__main__":
    asyncio.run(test_pos_admin_flow())
