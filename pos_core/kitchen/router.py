from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pos_core.database import get_session
from .models import KitchenTicket, KitchenTicketRead, KitchenStatus, ProductionAreaRead, ProductionArea
from .repository import kitchen_repo
from .services import update_ticket_status

router = APIRouter(tags=["Kitchen"])

@router.get("/tickets", response_model=List[KitchenTicketRead])
async def get_active_tickets(session: AsyncSession = Depends(get_session)):
    """Obtiene todos los tickets activos para el KDS."""
    return await kitchen_repo.get_active_tickets(session)

@router.post("/tickets/{ticket_id}/prepare")
async def start_preparing_ticket(
    ticket_id: int, 
    cook_uuid: str, 
    cook_name: str,
    session: AsyncSession = Depends(get_session)
):
    """Marca un ticket como 'En preparación'."""
    ticket = await update_ticket_status(session, ticket_id, KitchenStatus.PREPARING, cook_uuid, cook_name)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return {"status": "ok", "new_status": KitchenStatus.PREPARING}

@router.post("/tickets/{ticket_id}/ready")
async def finish_ticket(
    ticket_id: int, 
    session: AsyncSession = Depends(get_session)
):
    """Marca un ticket como 'Listo'."""
    ticket = await update_ticket_status(session, ticket_id, KitchenStatus.READY)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return {"status": "ok", "new_status": KitchenStatus.READY}

@router.get("/production-areas", response_model=List[ProductionAreaRead])
async def get_production_areas(session: AsyncSession = Depends(get_session)):
    from sqlalchemy import select
    result = await session.execute(select(ProductionArea))
    return result.scalars().all()
