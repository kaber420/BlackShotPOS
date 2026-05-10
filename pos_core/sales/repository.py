"""
pos_core/sales/repository.py
============================
Capa de Repositorio para el módulo de ventas.

REGLA FUNDAMENTAL:
  - Este archivo es el ÚNICO lugar donde SQLAlchemy accede a la BD del módulo de ventas.
  - Los métodos NUNCA hacen session.commit(). El control transaccional es del Servicio.
  - Los métodos NO contienen reglas de negocio (eso es responsabilidad del Servicio).
"""

from typing import List, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, desc

from .models import Order, OrderItem, Payment, OrderStatus, PaymentMethod
from pos_core.catalog.models import ProductVariant, Product


class OrderRepository:
    """
    Acceso a datos para la entidad Order y sus relaciones directas (Payment).
    """

    async def get_by_id(self, session: AsyncSession, order_id: int) -> Optional[Order]:
        """Obtiene una Order por PK, sin relaciones precargadas. Rápido y ligero."""
        return await session.get(Order, order_id)

    async def get_with_relations(
        self, session: AsyncSession, order_id: int
    ) -> Optional[Order]:
        """
        Obtiene una Order con TODAS sus relaciones precargadas (eager loading).
        Usar cuando se necesita acceder a items, variantes, modificadores o pagos.
        """
        statement = (
            select(Order)
            .where(Order.id == order_id)
            .options(
                selectinload(Order.items).selectinload(OrderItem.product).selectinload(Product.tax),
                selectinload(Order.items).selectinload(OrderItem.modifiers),
                selectinload(Order.items)
                .selectinload(OrderItem.variant)
                .selectinload(ProductVariant.measure),
                selectinload(Order.payments),
            )
        )
        result = await session.execute(statement)
        return result.unique().scalar_one_or_none()

    async def get_all(
        self,
        session: AsyncSession,
        status: Optional[OrderStatus] = None,
        shift_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        include_relations: bool = False,
    ) -> List[Order]:
        """
        Lista todas las órdenes con filtros opcionales y carga de relaciones.
        """
        statement = select(Order)
        if status is not None:
            statement = statement.where(Order.status == status)
        if shift_id is not None:
            statement = statement.where(Order.shift_id == shift_id)
        if start_date is not None:
            statement = statement.where(Order.created_at >= start_date)

        if include_relations:
            statement = statement.options(
                selectinload(Order.items).selectinload(OrderItem.product),
                selectinload(Order.items).selectinload(OrderItem.modifiers),
                selectinload(Order.items)
                .selectinload(OrderItem.variant)
                .selectinload(ProductVariant.measure),
                selectinload(Order.payments),
            )
        
        result = await session.execute(statement)
        return list(result.scalars().all())

    async def get_star_product_name(
        self, session: AsyncSession, start_date: datetime
    ) -> str:
        """
        Calcula el producto más vendido desde una fecha dada usando agregación SQL.
        Mucho más eficiente que cargar todas las órdenes en Python.
        """
        statement = (
            select(Product.name, func.sum(OrderItem.quantity).label("total_qty"))
            .join(OrderItem, OrderItem.product_id == Product.id)
            .join(Order, OrderItem.order_id == Order.id)
            .where(Order.created_at >= start_date)
            .where(Order.status != OrderStatus.CANCELLED)
            .group_by(Product.name)
            .order_by(desc("total_qty"))
            .limit(1)
        )
        result = await session.execute(statement)
        row = result.first()
        return row[0] if row else "Ninguno"



    async def save(self, session: AsyncSession, order: Order) -> None:
        """Agrega/actualiza un objeto Order en la sesión activa (sin commit)."""
        session.add(order)

    async def delete(self, session: AsyncSession, order: Order) -> None:
        """Elimina un objeto Order de la sesión activa (sin commit)."""
        await session.delete(order)

    async def create_payment(
        self,
        session: AsyncSession,
        order_id: int,
        method: PaymentMethod,
        amount: float,
        received_amount: float = 0.0,
        change_amount: float = 0.0,
        tip_amount: float = 0.0,
    ) -> Payment:
        """
        Construye y persiste un Payment en la sesión activa (sin commit).
        El Servicio es responsable de hacer commit() después de llamar este método.
        """
        payment = Payment(
            order_id=order_id, 
            method=method, 
            amount=amount,
            received_amount=received_amount,
            change_amount=change_amount,
            tip_amount=tip_amount
        )
        session.add(payment)
        return payment


class OrderItemRepository:
    """
    Acceso a datos para la entidad OrderItem.
    """

    async def get_by_id(
        self, session: AsyncSession, order_id: int, item_id: int, include_modifiers: bool = True
    ) -> Optional[OrderItem]:
        """Obtiene un OrderItem por PK dentro de una orden."""
        statement = select(OrderItem).where(
            OrderItem.id == item_id, OrderItem.order_id == order_id
        )
        if include_modifiers:
            statement = statement.options(selectinload(OrderItem.modifiers))
            
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def get_items_for_order(
        self, session: AsyncSession, order_id: int, include_modifiers: bool = True
    ) -> List[OrderItem]:
        """Retorna todos los ítems de una orden."""
        statement = select(OrderItem).where(OrderItem.order_id == order_id)
        if include_modifiers:
            statement = statement.options(selectinload(OrderItem.modifiers))
            
        result = await session.execute(statement)
        return list(result.scalars().all())

    async def save(self, session: AsyncSession, item: OrderItem) -> None:
        """Agrega/actualiza un OrderItem en la sesión activa (sin commit)."""
        session.add(item)


# ── Instancias singleton exportadas ───────────────────────────────────────────
# Importar estas instancias en service.py para evitar instanciar en cada llamada.
order_repo = OrderRepository()
item_repo = OrderItemRepository()
