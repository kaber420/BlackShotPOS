from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from pos_core.database import get_session
from pos_core.customers.schemas import CustomerCreate, CustomerRead, CustomerUpdate
from pos_core.customers.service import CustomerService
from pos_core.auth.dependencies import require_permission

router = APIRouter()

@router.post("/", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer_in: CustomerCreate,
    db: AsyncSession = Depends(get_session),
    _ = Depends(require_permission("can_take_orders"))
):
    # Verificar si ya existe el teléfono
    if customer_in.phone:
        existing = await CustomerService.get_by_phone(db, customer_in.phone)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un cliente con ese número de teléfono"
            )
    return await CustomerService.create(db, customer_in)

@router.get("/search", response_model=List[CustomerRead])
async def search_customers(
    q: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_session),
    _ = Depends(require_permission("can_take_orders"))
):
    return await CustomerService.search(db, q)

@router.get("/{customer_id}", response_model=CustomerRead)
async def get_customer(
    customer_id: UUID,
    db: AsyncSession = Depends(get_session),
    _ = Depends(require_permission("can_take_orders"))
):
    customer = await CustomerService.get_by_id(db, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return customer

@router.patch("/{customer_id}", response_model=CustomerRead)
async def update_customer(
    customer_id: UUID,
    customer_in: CustomerUpdate,
    db: AsyncSession = Depends(get_session),
    _ = Depends(require_permission("can_take_orders"))
):
    customer = await CustomerService.get_by_id(db, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return await CustomerService.update(db, customer, customer_in)
