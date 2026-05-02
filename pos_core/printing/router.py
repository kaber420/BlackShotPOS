"""
Router de impresión ESC/POS.

Expone dos familias de endpoints:
  - /print/{ticket|comanda}/{order_id}/raw   → devuelve bytes descargables (para WebUSB en el frontend)
  - /print/{ticket|comanda}/{order_id}/network → envía directamente a una impresora de red (IP en .env)
"""
from __future__ import annotations

import os
import socket
import logging

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from pos_core.database import get_session
from pos_core.sales.models import Order, OrderItem
from pos_core.settings.service import get_settings
from pos_core.auth.dependencies import require_role
from . import formatter

logger = logging.getLogger(__name__)

router = APIRouter()

async def _get_order_with_items(order_id: int, session: AsyncSession) -> Order:
    """Helper: carga una orden con todos sus items, productos, variantes y pagos."""
    statement = (
        select(Order)
        .where(Order.id == order_id)
        .options(
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.items).selectinload(OrderItem.modifiers),
            selectinload(Order.items).selectinload(OrderItem.variant),
            selectinload(Order.payments),
        )
    )
    result = await session.execute(statement)
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail=f"Orden #{order_id} no encontrada")
    return order


# ── Ticket de venta (Generación de datos) ────────────────────────────────────

@router.get(
    "/ticket/{order_id}/raw",
    summary="Descargar ticket de venta como bytes ESC/POS",
    description=(
        "Devuelve el ticket en formato binario ESC/POS. "
        "El frontend es el responsable de enviarlo a la impresora (USB, BT, etc)."
    ),
    tags=["Impresión"],
)
async def get_ticket_raw(
    order_id: int,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_role("cashier")),
):
    order = await _get_order_with_items(order_id, session)
    settings = await get_settings(session)
    data = formatter.format_ticket(order, settings)
    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"inline; filename=ticket_{order_id}.bin"},
    )


@router.get(
    "/ticket/{order_id}/html",
    summary="Ver ticket de venta en HTML (para imprimir desde el navegador)",
    response_class=HTMLResponse,
    tags=["Impresión"],
)
async def get_ticket_html(
    order_id: int,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_role("cashier")),
):
    order = await _get_order_with_items(order_id, session)
    settings = await get_settings(session)
    return formatter.format_ticket_html(order, settings)


# ── Comanda de cocina (Generación de datos) ──────────────────────────────────

@router.get(
    "/comanda/{order_id}/raw",
    summary="Descargar comanda de cocina como bytes ESC/POS",
    tags=["Impresión"],
)
async def get_comanda_raw(
    order_id: int,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_role("waiter")),
):
    order = await _get_order_with_items(order_id, session)
    settings = await get_settings(session)
    data = formatter.format_comanda(order, settings)
    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"inline; filename=comanda_{order_id}.bin"},
    )


@router.get(
    "/comanda/{order_id}/html",
    summary="Ver comanda de cocina en HTML (para imprimir desde el navegador)",
    response_class=HTMLResponse,
    tags=["Impresión"],
)
async def get_comanda_html(
    order_id: int,
    session: AsyncSession = Depends(get_session),
    user=Depends(require_role("waiter")),
):
    order = await _get_order_with_items(order_id, session)
    settings = await get_settings(session)
    return formatter.format_comanda_html(order, settings)
