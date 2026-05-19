import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from pos_core.database import async_session_maker, init_db
from pos_core.customers.service import CustomerService
from pos_core.customers.schemas import CustomerCreate

async def main():
    print("--- 🛍️ Creando Cliente de Prueba para el Portal Público (Argon2) ---")
    await init_db()
    
    async with async_session_maker() as session:
        username = "testcustomer"
        password = "securepassword123"
        email = "customer@blackshot.app"
        
        # Verificar si ya existe
        existing = await CustomerService.get_by_username(session, username)
        if existing:
            print(f"⚠️ El cliente '{username}' ya existe.")
            print(f"Username: {username}")
            print(f"Password: {password}")
            return
            
        c_in = CustomerCreate(
            name="Cliente de Prueba",
            phone="5551234567",
            email=email,
            username=username,
            password=password
        )
        
        try:
            customer = await CustomerService.create(session, c_in)
            print("\n✅ Cliente de prueba creado exitosamente!")
            print(f"Username: {customer.username}")
            print(f"Password: {password}")
            print(f"Email: {email}")
            print(f"Loyalty Code: {customer.loyalty_code}")
        except Exception as e:
            print(f"\n❌ Error al crear cliente: {e}")

if __name__ == "__main__":
    asyncio.run(main())
