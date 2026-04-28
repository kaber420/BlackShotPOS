from typing import Optional, Union
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from pos_core.auth.router import fastapi_users
from pos_core.auth.models import User, BridgeUser
from pos_core.auth.bridge import validate_bridge_token
from pos_core.roles import resolve_permissions, ROLE_PRESETS
from pos_core.settings.service import get_settings
from pos_core.database import get_session

current_user = fastapi_users.current_user()
current_user_optional = fastapi_users.current_user(optional=True)

async def get_current_active_user(
    user: Optional[User] = Depends(current_user_optional),
    bridge_token: Optional[str] = Header(None, alias="X-Blackshot-Bridge-Auth"),
    db: AsyncSession = Depends(get_session)
) -> Union[User, BridgeUser]:
    # 1. Intentar con Bridge primero (SaaS as Admin)
    if bridge_token:
        settings = await get_settings(db)
        if not settings.bridge_enabled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El acceso remoto (Bridge) está deshabilitado en esta sucursal"
            )
        if not settings.bridge_public_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Configuración de seguridad incompleta: Falta llave pública del Bridge"
            )
        # Validar el token usando RS256
        validate_bridge_token(bridge_token, settings.bridge_public_key)
        
        # Retornamos el objeto BridgeUser simulado
        return BridgeUser()

    # 2. Intentar con Staff Local
    if user:
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo")
        return user
        
    # 3. Ninguno funcionó
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Se requiere sesión de staff o token de bridge válido",
        headers={"WWW-Authenticate": "Bearer"},
    )

def require_role(role: str):
    async def role_dependency(user: User = Depends(get_current_active_user)):
        user_role = user.custom_metadata.get("role", "waiter")
        if user_role != role and user_role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere el rol: {role}"
            )
        return user
    return role_dependency

def require_permission(permission: str):
    async def permission_dependency(user: User = Depends(get_current_active_user)):
        user_role = user.custom_metadata.get("role", "waiter")
        user_permissions = user.custom_metadata.get("permissions", {})
        
        effective_permissions = resolve_permissions(user_role, user_permissions)
        
        if not effective_permissions.get(permission, False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso insuficiente: {permission}"
            )
        return user
    return permission_dependency


