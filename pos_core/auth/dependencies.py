from fastapi import Depends, HTTPException, status
from pos_core.auth.router import fastapi_users
from pos_core.auth.models import User
from pos_core.roles import resolve_permissions, ROLE_PRESETS

current_user = fastapi_users.current_user()

async def get_current_active_user(user: User = Depends(current_user)):
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo")
    return user

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
