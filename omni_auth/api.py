from fastapi import APIRouter, Depends, HTTPException, Header, Request
from typing import Optional
import os
from .manager import OmniAuthManager
from .security import verify_omni_token, API_KEY_NAME
from .vault import vault
from .models import (
    LoginRequest, RegisterRequest, UserUpdateRequest, 
    PasswordChangeRequest, ElevateRequest, RefreshRequest,
    VaultEncryptRequest, VaultDecryptRequest, TokenResponse,
    UserInfo, MessageResponse
)
from . import database

router = APIRouter(prefix="/_auth", tags=["auth"])
auth_manager = OmniAuthManager()

@router.get("/verify")
async def verify(user_info: dict = Depends(verify_omni_token)):
    """Verifies the current token and returns user details."""
    return user_info

@router.get("/info")
async def get_auth_info():
    """Returns information about allowed auth methods for the UI."""
    methods = os.getenv("OMNI_AUTH_METHODS", "token,password").split(",")
    return {
        "methods": [m.strip() for m in methods],
        "mfa_enabled": True
    }

@router.get("/me")
async def get_current_user(user_info: dict = Depends(verify_omni_token)):
    """Retorna el perfil del usuario autenticado."""
    return {
        "uuid": user_info["user_uuid"],
        "username": user_info["username"],
        "role": user_info["role"],
        "is_elevated": user_info.get("is_elevated", False)
    }

@router.post("/elevate")
async def elevate(
    body: ElevateRequest,
    x_omni_token: str = Header(..., alias=API_KEY_NAME)
):
    """Elevates the current session using a TOTP code."""
    success = auth_manager.elevate_session(x_omni_token, body.otp)
    if success:
        return {"status": "elevated", "message": "Session elevated successfully."}
    raise HTTPException(status_code=403, detail="Invalid OTP code.")

@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    """Authenticates a user with username and password."""
    res = auth_manager.login(body.username, body.password)
    if res:
        return res
    raise HTTPException(status_code=401, detail="Invalid username or password.")

@router.post("/logout")
async def logout(user_info: dict = Depends(verify_omni_token)):
    """Revoca el token actual del usuario."""
    auth_manager.revoke_token(user_info["token"])
    return {"status": "ok", "message": "Sesión cerrada."}

@router.post("/logout-all")
async def logout_all(user_info: dict = Depends(verify_omni_token)):
    """Revoca TODAS las sesiones del usuario actual."""
    database.revoke_all_user_tokens(user_info["user_uuid"])
    return {"status": "ok", "message": "Todas las sesiones cerradas."}

@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest):
    """Generates a new access token using a refresh token."""
    res = auth_manager.refresh_session(body.refresh_token)
    if res:
        return res
    raise HTTPException(status_code=401, detail="Invalid or expired refresh token.")

@router.post("/register", response_model=TokenResponse)
async def register(
    body: RegisterRequest,
    user_info: dict = Depends(verify_omni_token)
):
    """Registers a new user (Requires Admin)."""
    if user_info["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admins can register users.")
        
    res = auth_manager.register_user_with_token(
        body.username, 
        role=body.role, 
        enable_mfa=body.enable_mfa, 
        password=body.password
    )
    return res

# === User Management CRUD ===

@router.get("/users")
async def list_users(
    include_inactive: bool = False,
    user_info: dict = Depends(verify_omni_token)
):
    """Lista todos los usuarios (Solo Admin)."""
    if user_info["role"] != "admin":
        raise HTTPException(status_code=403, detail="Solo admins pueden listar usuarios.")
    return database.list_users(include_inactive=include_inactive)

@router.get("/users/{user_uuid}")
async def get_user(
    user_uuid: str,
    user_info: dict = Depends(verify_omni_token)
):
    """Obtiene un usuario por UUID (Solo Admin)."""
    if user_info["role"] != "admin":
        raise HTTPException(status_code=403, detail="Solo admins pueden ver usuarios.")
    user = database.get_user(user_uuid=user_uuid)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return {
        "uuid": user["uuid"],
        "username": user["username"],
        "role": user.get("role", "operator"),
        "is_active": user.get("is_active", 1),
        "mfa_enabled": bool(user["mfa_enabled"]),
        "created_at": user["created_at"]
    }

@router.put("/users/{user_uuid}")
async def update_user(
    user_uuid: str,
    body: UserUpdateRequest,
    user_info: dict = Depends(verify_omni_token)
):
    """Actualiza un usuario. Solo admin."""
    if user_info["role"] != "admin":
        raise HTTPException(status_code=403, detail="Solo admins pueden editar usuarios.")
    success = database.update_user(
        user_uuid,
        username=body.username,
        role=body.role,
        is_active=body.is_active
    )
    if not success:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    return {"status": "ok", "message": "Usuario actualizado."}

@router.delete("/users/{user_uuid}")
async def deactivate_user(
    user_uuid: str,
    user_info: dict = Depends(verify_omni_token)
):
    """Desactiva un usuario y revoca sus tokens. Solo admin."""
    if user_info["role"] != "admin":
        raise HTTPException(status_code=403, detail="Solo admins pueden desactivar usuarios.")
    if user_uuid == user_info["user_uuid"]:
        raise HTTPException(status_code=400, detail="No puedes desactivarte a ti mismo.")
    database.update_user(user_uuid, is_active=0)
    database.revoke_all_user_tokens(user_uuid)
    return {"status": "ok", "message": "Usuario desactivado y sesiones revocadas."}

@router.put("/users/{user_uuid}/password")
async def change_password(
    user_uuid: str,
    body: PasswordChangeRequest,
    user_info: dict = Depends(verify_omni_token)
):
    """Cambia la contraseña. Admin puede cambiar la de cualquiera, otros solo la suya."""
    if user_info["role"] != "admin" and user_info["user_uuid"] != user_uuid:
        raise HTTPException(status_code=403, detail="Solo puedes cambiar tu propia contraseña.")
    pwd_hash = auth_manager._hash_password(body.new_password)
    database.update_user_password(user_uuid, pwd_hash)
    return {"status": "ok", "message": "Contraseña actualizada."}

@router.get("/audit")
async def get_audit_log(
    limit: int = 50,
    user_info: dict = Depends(verify_omni_token)
):
    """Retorna el audit log. Solo admin."""
    if user_info["role"] != "admin":
        raise HTTPException(status_code=403, detail="Solo admins pueden ver el audit log.")
    return database.get_audit_log(limit=limit)

@router.post("/vault/encrypt")
async def vault_encrypt(body: VaultEncryptRequest, user_info: dict = Depends(verify_omni_token)):
    """Encrypts data for the current user."""
    return {"encrypted": vault.encrypt(user_info["user_uuid"], body.plaintext)}

@router.post("/vault/decrypt")
async def vault_decrypt(body: VaultDecryptRequest, user_info: dict = Depends(verify_omni_token)):
    """Decrypts data for the current user."""
    try:
        return {"decrypted": vault.decrypt(user_info["user_uuid"], body.encrypted_data)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

def include_omni_auth_router(app):
    app.include_router(router)
