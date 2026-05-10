from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from .models import KitchenTicket, KitchenStatus, ProductionArea

class KitchenRepository:
    async def get_ticket_by_id(self, session: AsyncSession, ticket_id: int) -> Optional[KitchenTicket]:
        return await session.get(KitchenTicket, ticket_id)

    async def get_active_tickets(self, session: AsyncSession) -> List[KitchenTicket]:
        """Retorna tickets que no han sido entregados ni cancelados."""
        statement = (
            select(KitchenTicket)
            .where(KitchenTicket.status.in_([KitchenStatus.PENDING, KitchenStatus.PREPARING, KitchenStatus.READY]))
            .order_by(KitchenTicket.received_at.asc())
            .options(selectinload(KitchenTicket.production_area))
        )
        result = await session.execute(statement)
        return result.scalars().all()

    async def get_tickets_by_order(self, session: AsyncSession, order_id: int) -> List[KitchenTicket]:
        statement = select(KitchenTicket).where(KitchenTicket.order_id == order_id)
        result = await session.execute(statement)
        return result.scalars().all()

    async def save(self, session: AsyncSession, ticket: KitchenTicket) -> KitchenTicket:
        session.add(ticket)
        return ticket

    async def get_ticket_by_item_id(self, session: AsyncSession, item_id: int) -> Optional[KitchenTicket]:
        """Busca el ticket activo asociado a un ítem de venta."""
        statement = (
            select(KitchenTicket)
            .where(KitchenTicket.item_id == item_id)
            .where(KitchenTicket.status != KitchenStatus.CANCELLED)
        )
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def delete_tickets_by_order(self, session: AsyncSession, order_id: int):
        statement = select(KitchenTicket).where(KitchenTicket.order_id == order_id)
        result = await session.execute(statement)
        tickets = result.scalars().all()
        for t in tickets:
            await session.delete(t)

kitchen_repo = KitchenRepository()
