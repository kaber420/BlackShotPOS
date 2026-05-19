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

from typing import List
from sqlmodel import select
from pos_core.customers.schemas import CustomerOrderRead, CustomerOrderItemRead, CustomerStatsRead
from pos_core.sales.models import Order, OrderItem, Payment
from pos_core.catalog.models import Product, ProductVariant, Measure
from pos_core.settings.models import BusinessSettings
from collections import Counter

@router.get("/me/orders", response_model=List[CustomerOrderRead])
@limiter.limit("20/minute")
async def get_my_orders(
    request: Request,
    db: AsyncSession = Depends(get_session),
    current_customer: Customer = Depends(get_current_customer)
):
    # 1. Obtener el nombre de la sucursal actual
    settings_statement = select(BusinessSettings).where(BusinessSettings.id == 1)
    settings_result = await db.execute(settings_statement)
    settings = settings_result.scalar_one_or_none()
    branch_name = settings.name if settings else "Blackshot Coffee"

    # 2. Buscar todas las órdenes del cliente
    statement = (
        select(Order)
        .where(Order.customer_id == current_customer.id)
        .order_by(Order.created_at.desc())
    )
    result = await db.execute(statement)
    orders = result.scalars().all()

    response_orders = []
    for order in orders:
        # Cargar los ítems con sus productos y variantes
        items_statement = (
            select(OrderItem)
            .where(OrderItem.order_id == order.id)
        )
        items_result = await db.execute(items_statement)
        items = items_result.scalars().all()

        response_items = []
        for item in items:
            # Cargar producto
            prod_stmt = select(Product).where(Product.id == item.product_id)
            prod_res = await db.execute(prod_stmt)
            product = prod_res.scalar_one_or_none()
            product_name = product.name if product else "Producto Desconocido"

            # Cargar medida si hay variante
            measure_name = None
            if item.product_variant_id:
                var_stmt = select(ProductVariant).where(ProductVariant.id == item.product_variant_id)
                var_res = await db.execute(var_stmt)
                variant = var_res.scalar_one_or_none()
                if variant and variant.measure_id:
                    meas_stmt = select(Measure).where(Measure.id == variant.measure_id)
                    meas_res = await db.execute(meas_stmt)
                    measure = meas_res.scalar_one_or_none()
                    if measure:
                        measure_name = measure.name

            response_items.append(
                CustomerOrderItemRead(
                    product_name=product_name,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    measure_name=measure_name
                )
            )

        # Cargar métodos de pago
        payments_statement = (
            select(Payment)
            .where(Payment.order_id == order.id)
        )
        payments_result = await db.execute(payments_statement)
        payments = payments_result.scalars().all()
        payment_methods = list(set([p.method.value for p in payments]))

        response_orders.append(
            CustomerOrderRead(
                id=order.id,
                created_at=order.created_at,
                branch_name=branch_name,
                total_amount=order.total_amount,
                financial_status=order.financial_status.value,
                items=response_items,
                payment_methods=payment_methods
            )
        )

    return response_orders

@router.get("/me/stats", response_model=CustomerStatsRead)
@limiter.limit("20/minute")
async def get_my_stats(
    request: Request,
    db: AsyncSession = Depends(get_session),
    current_customer: Customer = Depends(get_current_customer)
):
    # 1. Obtener el nombre de la sucursal actual
    settings_statement = select(BusinessSettings).where(BusinessSettings.id == 1)
    settings_result = await db.execute(settings_statement)
    settings = settings_result.scalar_one_or_none()
    branch_name = settings.name if settings else "Blackshot Coffee"

    # 2. Buscar todas las órdenes del cliente
    statement = (
        select(Order)
        .where(Order.customer_id == current_customer.id)
    )
    result = await db.execute(statement)
    orders = result.scalars().all()

    total_visits = len(orders)
    total_spent = sum(order.total_amount for order in orders)

    # 3. Determinar el producto estrella (favorito)
    product_names = []
    for order in orders:
        items_statement = select(OrderItem).where(OrderItem.order_id == order.id)
        items_result = await db.execute(items_statement)
        items = items_result.scalars().all()
        for item in items:
            prod_stmt = select(Product).where(Product.id == item.product_id)
            prod_res = await db.execute(prod_stmt)
            product = prod_res.scalar_one_or_none()
            if product:
                product_names.extend([product.name] * item.quantity)

    favorite_product = None
    if product_names:
        counts = Counter(product_names)
        favorite_product = counts.most_common(1)[0][0]

    return CustomerStatsRead(
        total_visits=total_visits,
        total_spent=total_spent,
        favorite_product=favorite_product,
        favorite_branch=branch_name,
        last_visit_at=current_customer.last_visit_at
    )

