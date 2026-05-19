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
        print("\n🎉 ¡Todas las pruebas de administración de clientes pasaron con éxito! 🎉")

if __name__ == "__main__":
    asyncio.run(test_pos_admin_flow())
