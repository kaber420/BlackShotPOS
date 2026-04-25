import sys
import os
import asyncio

# Añadir el directorio raíz al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from omni_auth.manager import OmniAuthManager

async def main():
    print("--- Creando Usuario Administrador Inicial ---")
    auth_manager = OmniAuthManager()
    
    username = "admin"
    password = "admin_password" # El usuario debería cambiar esto
    role = "admin"
    
    print(f"Registrando usuario: {username} con rol: {role}...")
    
    try:
        res = auth_manager.register_user_with_token(
            username=username,
            password=password,
            role=role,
            enable_mfa=False
        )
        print("\n✅ Usuario creado exitosamente!")
        print(f"Username: {username}")
        print(f"Password: {password}")
        print(f"Token: {res['token']}")
        print("\nGuarda estas credenciales para tu primer login.")
    except Exception as e:
        print(f"\n❌ Error al crear usuario: {e}")

if __name__ == "__main__":
    asyncio.run(main())
