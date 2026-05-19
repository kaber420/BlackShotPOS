from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pydantic import BaseModel

from pos_core.database import get_session
from pos_core.customers.models import Customer
from pos_core.customers.service import CustomerService
from pos_core.customers.schemas import CustomerRead
from pos_core.auth.dependencies import get_current_customer
from pos_core.auth.customer_jwt import create_customer_access_token
from pos_core.security import limiter

router = APIRouter()

class CustomerLoginRequest(BaseModel):
    username: str
    password: str

class CustomerRegisterRequest(BaseModel):
    phone: str
    name: str
    pin: str

class CustomerTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/auth/register", response_model=CustomerTokenResponse)
@limiter.limit("5/minute")
async def customer_register(
    request: Request,
    register_data: CustomerRegisterRequest,
    db: AsyncSession = Depends(get_session)
):
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="El auto-registro está deshabilitado. Por favor, acérquese a la caja para registrarse."
    )

@router.post("/auth/login", response_model=CustomerTokenResponse)
@limiter.limit("5/minute")
async def customer_login(
    request: Request,
    login_data: CustomerLoginRequest,
    db: AsyncSession = Depends(get_session)
):
    # 1. Búsqueda Local por username
    customer = await CustomerService.get_by_username(db, login_data.username)
    
    # 2. Si no existe, rechazamos la conexión
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nombre de usuario no registrado."
        )
    
    # 3. Validar Password
    if not customer.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cuenta no configurada con contraseña. Por favor, contacta al personal."
        )
    
    from pos_core.crypto import CryptoService
    if not CryptoService.verify_password(login_data.password, customer.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Contraseña incorrecta."
        )
    
    # Generar Token
    access_token = create_customer_access_token({"sub": str(customer.id)})
    
    # Actualizar última visita
    await CustomerService.update_last_visit(db, customer.id)
    
    return CustomerTokenResponse(access_token=access_token)

@router.get("/me", response_model=CustomerRead)
@limiter.limit("30/minute")
async def get_my_profile(
    request: Request,
    current_customer: Customer = Depends(get_current_customer)
):
    return current_customer

class PreferencesUpdate(BaseModel):
    custom_metadata: dict

@router.patch("/me/preferences", response_model=CustomerRead)
@limiter.limit("10/minute")
async def update_my_preferences(
    request: Request,
    preferences: PreferencesUpdate,
    db: AsyncSession = Depends(get_session),
    current_customer: Customer = Depends(get_current_customer)
):
    from pos_core.customers.schemas import CustomerUpdate
    update_schema = CustomerUpdate(custom_metadata=preferences.custom_metadata)
    updated_customer = await CustomerService.update(db, current_customer, update_schema)
    return updated_customer
