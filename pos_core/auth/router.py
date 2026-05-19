from fastapi import APIRouter, Depends, HTTPException
from fastapi_users import FastAPIUsers
from pos_core.auth.models import User
from pos_core.auth.schemas import UserRead, UserCreate, UserUpdate
from pos_core.auth.manager import get_user_manager, UserManager
from pos_core.auth.backend import auth_backend
from uuid import UUID
from typing import List
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from pos_core.database import get_session
from fastapi_users.db import SQLAlchemyUserDatabase
from pos_core.events.bus import event_bus
from pos_core.roles import resolve_permissions

fastapi_users = FastAPIUsers[User, UUID](
    get_user_manager,
    [auth_backend],
)

auth_router = APIRouter()

# Rutas de login/logout
auth_router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/jwt",
    tags=["Auth"],
)

# Rutas de gestión de usuarios (/me, etc)
user_router = fastapi_users.get_users_router(UserRead, UserUpdate)

# --- LOCAL DEPENDENCY TO AVOID CIRCULAR IMPORTS ---

async def check_manage_users(current_user: User = Depends(fastapi_users.current_user())):
    user_role = current_user.custom_metadata.get("role", "waiter") if current_user.custom_metadata else "waiter"
    user_permissions = current_user.custom_metadata.get("permissions", {}) if current_user.custom_metadata else {}
    
    effective_permissions = resolve_permissions(user_role, user_permissions)
    
    if not effective_permissions.get("can_manage_users", False):
        raise HTTPException(
            status_code=403,
            detail="Permiso insuficiente: can_manage_users"
        )
    return current_user

# --- CUSTOM BACKEND ROUTES ---

# 1. Custom register endpoint under auth_router
@auth_router.post("/register")
async def register_user(
    payload: dict,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_manage_users)
):
    username = payload.get("username")
    password = payload.get("password")
    role = payload.get("role", "waiter")
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="Nombre de usuario y contraseña requeridos")
        
    username_clean = username.strip()
    email = f"{username_clean.lower()}@local.pos"
    
    stmt = select(User).where((User.email == email) | (User.username == username_clean))
    res = await db.execute(stmt)
    if res.scalars().first():
        raise HTTPException(status_code=400, detail="El usuario ya existe")
        
    user_db = SQLAlchemyUserDatabase(db, User)
    user_manager = UserManager(user_db)
    hashed_password = user_manager.password_helper.hash(password)
    
    new_user = User(
        email=email,
        username=username_clean,
        hashed_password=hashed_password,
        is_active=True,
        is_superuser=(role == "admin"),
        is_verified=True,
        organization_id="default",
        custom_metadata={
            "role": role,
            "permissions": {}
        }
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    await event_bus.publish("auth.user_registered", {"user_id": str(new_user.id), "email": new_user.email})
    
    return {
        "uuid": str(new_user.id),
        "username": new_user.username,
        "role": role,
        "is_active": 1,
        "mfa_enabled": False,
        "created_at": "",
        "permissions": {}
    }

# 2. List all users under user_router
@user_router.get("", response_model=List[dict])
async def list_users(
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_manage_users)
):
    stmt = select(User)
    if not include_inactive:
        stmt = stmt.where(User.is_active == True)
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    response = []
    for u in users:
        response.append({
            "uuid": str(u.id),
            "username": u.username,
            "role": u.custom_metadata.get("role", "waiter") if u.custom_metadata else "waiter",
            "is_active": 1 if u.is_active else 0,
            "mfa_enabled": False,
            "created_at": "",
            "permissions": u.custom_metadata.get("permissions", {}) if u.custom_metadata else {}
        })
    return response

# 3. Get single user by uuid under user_router
@user_router.get("/{uuid}", response_model=dict)
async def get_user_detail(
    uuid: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_manage_users)
):
    stmt = select(User).where(User.id == uuid)
    res = await db.execute(stmt)
    u = res.scalars().first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    return {
        "uuid": str(u.id),
        "username": u.username,
        "role": u.custom_metadata.get("role", "waiter") if u.custom_metadata else "waiter",
        "is_active": 1 if u.is_active else 0,
        "mfa_enabled": False,
        "created_at": "",
        "permissions": u.custom_metadata.get("permissions", {}) if u.custom_metadata else {}
    }

# 4. Patch user base fields under user_router
@user_router.patch("/{uuid}", response_model=dict)
async def update_user(
    uuid: UUID,
    payload: dict,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_manage_users)
):
    stmt = select(User).where(User.id == uuid)
    res = await db.execute(stmt)
    u = res.scalars().first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    if "is_active" in payload:
        u.is_active = bool(payload["is_active"])
        
    if "role" in payload:
        if not u.custom_metadata:
            u.custom_metadata = {}
        u.custom_metadata["role"] = payload["role"]
        
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(u, "custom_metadata")
    
    db.add(u)
    await db.commit()
    await db.refresh(u)
    
    return {
        "uuid": str(u.id),
        "username": u.username,
        "role": u.custom_metadata.get("role", "waiter") if u.custom_metadata else "waiter",
        "is_active": 1 if u.is_active else 0,
        "mfa_enabled": False,
        "created_at": "",
        "permissions": u.custom_metadata.get("permissions", {}) if u.custom_metadata else {}
    }

# 5. Delete/Deactivate user under user_router
@user_router.delete("/{uuid}")
async def deactivate_user(
    uuid: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_manage_users)
):
    stmt = select(User).where(User.id == uuid)
    res = await db.execute(stmt)
    u = res.scalars().first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    u.is_active = False
    db.add(u)
    await db.commit()
    return {"status": "success", "message": "Usuario desactivado"}

# 6. Override individual permission under user_router
@user_router.patch("/{uuid}/permissions")
async def update_user_permissions(
    uuid: UUID,
    payload: dict,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_manage_users)
):
    stmt = select(User).where(User.id == uuid)
    res = await db.execute(stmt)
    u = res.scalars().first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    if not u.custom_metadata:
        u.custom_metadata = {}
    if "permissions" not in u.custom_metadata:
        u.custom_metadata["permissions"] = {}
        
    for k, v in payload.items():
        u.custom_metadata["permissions"][k] = bool(v)
        
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(u, "custom_metadata")
    
    db.add(u)
    await db.commit()
    return {"status": "success"}

# 7. Reset individual permission under user_router
@user_router.delete("/{uuid}/permissions/{perm}")
async def reset_user_permission(
    uuid: UUID,
    perm: str,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_manage_users)
):
    stmt = select(User).where(User.id == uuid)
    res = await db.execute(stmt)
    u = res.scalars().first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    if u.custom_metadata and "permissions" in u.custom_metadata:
        if perm in u.custom_metadata["permissions"]:
            del u.custom_metadata["permissions"][perm]
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(u, "custom_metadata")
            db.add(u)
            await db.commit()
            
    return {"status": "success"}

# 8. Force password change under user_router
@user_router.put("/{uuid}/password")
async def change_user_password(
    uuid: UUID,
    payload: dict,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(check_manage_users)
):
    new_password = payload.get("new_password")
    if not new_password:
        raise HTTPException(status_code=400, detail="Nueva contraseña requerida")
        
    stmt = select(User).where(User.id == uuid)
    res = await db.execute(stmt)
    u = res.scalars().first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    user_db = SQLAlchemyUserDatabase(db, User)
    user_manager = UserManager(user_db)
    hashed_password = user_manager.password_helper.hash(new_password)
    
    u.hashed_password = hashed_password
    db.add(u)
    await db.commit()
    return {"status": "success", "message": "Contraseña actualizada correctamente"}
