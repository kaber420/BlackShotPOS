import asyncio
from pos_core.database import async_session_maker
from pos_core.auth.models import User
from pos_core.auth.manager import UserManager
from fastapi_users.db import SQLAlchemyUserDatabase
import uuid

async def create_admin():
    async with async_session_maker() as session:
        user_db = SQLAlchemyUserDatabase(session, User)
        user_manager = UserManager(user_db)
        
        email = "kaber@blackshot.com"
        password = "admin1234"
        
        # Verificar si ya existe
        try:
            existing_user = await user_manager.get_by_email(email)
            print(f"El usuario {email} ya existe.")
            return
        except Exception:
            pass

        # Hashear la contraseña manualmente usando el helper del manager
        hashed_password = user_manager.password_helper.hash(password)
        
        new_user = User(
            email=email,
            hashed_password=hashed_password,
            is_active=True,
            is_superuser=True,
            is_verified=True,
            organization_id="main",
            custom_metadata={
                "role": "admin",
                "permissions": {}
            }
        )
        
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        
        print(f"✅ Usuario administrador creado: {email}")
        print(f"ID: {new_user.id}")

if __name__ == "__main__":
    asyncio.run(create_admin())
