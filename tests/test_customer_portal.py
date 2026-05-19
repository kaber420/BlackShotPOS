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
from pos_core.crypto import CryptoService

async def test_portal_flow():
    print("--- 🧪 Test de Integración: Portal de Clientes Local ---")
    await init_db()
    
    async with async_session_maker() as session:
        # 1. Crear un cliente simulando la acción de Staff en la Caja
        print("\n1. Staff crea un cliente de prueba con Username y Password...")
        username = "testcustomer"
        password = "securepassword123"
        
        # Eliminar si ya existe para evitar conflictos
        existing = await CustomerService.get_by_username(session, username)
        if existing:
            print("Cliente previo encontrado. Eliminándolo para una prueba limpia...")
            await session.delete(existing)
            await session.commit()
        
        c_in = CustomerCreate(
            name="Alejandro Sanz",
            phone="5512341234",
            email="ale@example.com",
            username=username,
            password=password  # Se hashea en el Service con Argon2
        )
        
        customer = await CustomerService.create(session, c_in)
        print(f"✅ Cliente creado por Staff: {customer.name}")
        print(f"   Username: {customer.username}")
        print(f"   Loyalty Code: {customer.loyalty_code}")
        print(f"   Tier: {customer.tier}")
        
        # 2. Verificar autenticación local (Login)
        print("\n2. Simulando inicio de sesión en el Portal Público...")
        found = await CustomerService.get_by_username(session, username)
        if not found:
            print("❌ Error: Cliente no encontrado en la base de datos.")
            return
            
        # Verificar contraseña
        is_valid = CryptoService.verify_password(password, found.hashed_password)
        if is_valid:
            print("✅ Contraseña verificada exitosamente con Argon2.")
        else:
            print("❌ Error: Verificación de contraseña fallida.")
            return

        # 3. Simular generación de JWT Token
        from pos_core.auth.customer_jwt import create_customer_access_token, decode_customer_access_token
        token = create_customer_access_token({"sub": str(customer.id)})
        print(f"✅ JWT Token generado con éxito: {token[:30]}...")
        
        # Decodificar y validar token
        payload = decode_customer_access_token(token)
        if payload and payload.get("sub") == str(customer.id) and payload.get("role") == "customer":
            print("✅ JWT Token decodificado y validado con éxito (Rol: customer).")
        else:
            print("❌ Error: Falló la decodificación o validación del JWT.")
            return

        # 4. Modificar preferencias del cliente
        print("\n4. Simulando actualización de preferencias desde el portal...")
        update_schema = CustomerUpdate(
            custom_metadata={
                "preferences_notes": "Cortado con leche de avena bien caliente",
                "allergies": "Gluten"
            }
        )
        updated = await CustomerService.update(session, found, update_schema)
        print(f"✅ Preferencias actualizadas:")
        print(f"   Notas: {updated.custom_metadata.get('preferences_notes')}")
        print(f"   Alergias: {updated.custom_metadata.get('allergies')}")
        
        # Limpieza final
        print("\nLimpiando datos de prueba...")
        await session.delete(updated)
        await session.commit()
        print("✅ Limpieza completada.")
        print("\n🎉 ¡Todas las pruebas de integración del portal de clientes pasaron con éxito! 🎉")

if __name__ == "__main__":
    asyncio.run(test_portal_flow())
