"""
pos_core/sales/audit_service.py
===============================
Servicio de Auditoría: Centraliza el registro de acciones sensibles en el sistema.
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from .models import AuditLog, AuditCategory

async def log_action(
    session: AsyncSession,
    category: AuditCategory,
    action: str,
    actor_uuid: str,
    actor_name: str,
    reason: Optional[str] = None,
    target_id: Optional[str] = None,
    target_type: Optional[str] = None,
    changes_json: Optional[str] = None,
) -> AuditLog:
    """
    Registra una acción en el log de auditoría.
    Este método se encarga puramente de la persistencia del log.
    """
    log = AuditLog(
        category=category,
        action=action,
        reason=reason,
        actor_uuid=actor_uuid,
        actor_name=actor_name,
        target_id=target_id,
        target_type=target_type,
        changes_json=changes_json,
        timestamp=datetime.now(timezone.utc)
    )
    session.add(log)
    # Nota: No hacemos commit aquí, dejamos que el orquestador (Service o Router) lo haga.
    return log
