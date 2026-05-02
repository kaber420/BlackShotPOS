import sys
import os
import asyncio
from uuid import UUID

# Añadir el directorio raíz al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pos_core.database import async_session_maker, init_db
from pos_core.auth.models import User
from pos_core.auth.db import SQLAlchemyUserDatabase
from pos_core.auth.manager import UserManager
from pos_core.auth.schemas import UserCreate

async def main():
    print("--- 🛡️ Creando Usuario Administrador Inicial (FastAPI Users) ---")
    
    # Asegurar que las tablas existan
    await init_db()
    
    async with async_session_maker() as session:
        user_db = SQLAlchemyUserDatabase(session, User)
        user_manager = UserManager(user_db)
        
        email = "admin@blackshot.pos"
        password = "admin1234" # Se recomienda cambiar esto tras el primer login
        role = "admin"
        
        print(f"Registrando usuario: {email} con rol: {role}...")
        
        user_create = UserCreate(
            email=email,
            password=password,
            organization_id="default",
            custom_metadata={"role": role, "permissions": {}}
        )
        
        try:
            user = await user_manager.create(user_create, safe=False)
            print("\n✅ Usuario creado exitosamente!")
            print(f"Email: {user.email}")
            print(f"Password: {password}")
            print(f"UUID: {user.id}")
            print("\nUsa estas credenciales para acceder al sistema.")
        except Exception as e:
            if "already exists" in str(e).lower() or "unique constraint" in str(e).lower():
                print(f"\n⚠️ El usuario {email} ya existe.")
            else:
                print(f"\n❌ Error al crear usuario: {e}")

if __name__ == "__main__":
    asyncio.run(main())
