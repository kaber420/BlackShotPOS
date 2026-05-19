import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pos_core.database import async_session_maker
from pos_core.auth.models import User
from pos_core.customers.models import Customer
from sqlmodel import select

async def main():
    try:
        print("=== 🔍 INSPECCIONANDO TABLAS DE USUARIOS Y CLIENTES ===")
        async with async_session_maker() as session:
            # Query Users (POS Staff / Admins)
            print("\n--- 👥 POS Staff (User Table) ---")
            statement_users = select(User)
            result_users = await session.execute(statement_users)
            users = result_users.scalars().all()
            print(f"Total: {len(users)}")
            for u in users:
                print(f"- Email: {u.email} | Username: {u.username} | Activo: {u.is_active} | Superuser: {u.is_superuser}")

            # Query Customers
            print("\n--- 🛍️ Customers (Customer Table) ---")
            statement_cust = select(Customer)
            result_cust = await session.execute(statement_cust)
            customers = result_cust.scalars().all()
            print(f"Total: {len(customers)}")
            for c in customers:
                # Some fields might be encrypted based on earlier conversations?
                # Let's see what fields exist
                print(f"- ID: {c.id} | Name: {getattr(c, 'name', 'N/A')} | Username: {getattr(c, 'username', 'N/A')} | Hashed Password: {getattr(c, 'hashed_password', 'N/A') is not None}")

    except Exception as e:
        print(f"\n❌ Error al consultar la base de datos: {e}")

if __name__ == "__main__":
    asyncio.run(main())
