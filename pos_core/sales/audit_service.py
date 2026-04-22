"""
pos_core/sales/audit_service.py
===============================
Servicio de Auditoría: Centraliza el registro de acciones sensibles en el sistema.
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from .models import AuditLog, AuditAction

async def log_action(
    session: AsyncSession,
    action: AuditAction,
    reason: str,
    actor_uuid: str,
    actor_name: str,
    order_id: Optional[int] = None,
    order_item_id: Optional[int] = None,
) -> AuditLog:
    """
    Registra una acción en el log de auditoría.
    Este método se encarga puramente de la persistencia del log.
    """
    log = AuditLog(
        action=action,
        reason=reason,
        actor_uuid=actor_uuid,
        actor_name=actor_name,
        order_id=order_id,
        order_item_id=order_item_id,
        timestamp=datetime.now(timezone.utc)
    )
    session.add(log)
    # Nota: No hacemos commit aquí, dejamos que el orquestador (Service o Router) lo haga.
    return log
