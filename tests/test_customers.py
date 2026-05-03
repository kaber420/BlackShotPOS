import sys
import os
import asyncio
from uuid import UUID

# Añadir el directorio raíz al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pos_core.database import async_session_maker, init_db
from pos_core.customers.models import Customer
from pos_core.customers.service import CustomerService
from pos_core.customers.schemas import CustomerCreate, CustomerUpdate

async def test_customers():
    print("--- 🧪 Test de Módulo de Clientes ---")
    await init_db()
    
    async with async_session_maker() as session:
        # 1. Crear un cliente
        print("\n1. Creando cliente...")
        c_in = CustomerCreate(
            name="Juan Perez",
            phone="5512345678",
            email="juan@example.com"
        )
        try:
            customer = await CustomerService.create(session, c_in)
            print(f"✅ Cliente creado: {customer.name} (ID: {customer.id})")
            
            # 2. Buscar por teléfono
            print("\n2. Buscando por teléfono 5512345678...")
            found = await CustomerService.get_by_phone(session, "5512345678")
            if found:
                print(f"✅ Encontrado: {found.name}")
            
            # 3. Actualizar teléfono (Verificar que el UUID se mantiene)
            print("\n3. Actualizando teléfono a 5599999999...")
            old_id = found.id
            update_in = CustomerUpdate(phone="5599999999")
            updated = await CustomerService.update(session, found, update_in)
            
            if updated.id == old_id:
                print(f"✅ Éxito: El UUID se mantuvo ({updated.id})")
                print(f"Nuevo teléfono: {updated.phone}")
            else:
                print(f"❌ Error: El UUID cambió!")

            # 4. Sumar puntos
            print("\n4. Sumando 100 puntos...")
            with_points = await CustomerService.add_points(session, updated.id, 100)
            print(f"✅ Puntos actuales: {with_points.points}")
            print(f"Sincronizado: {with_points.is_synced} (Debe ser False)")

        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_customers())
