import logging
import json
from pos_core.events.bus import on_event
from pos_core.database import async_session_maker
from pos_core.audit.models import AuditLog, AuditCategory

logger = logging.getLogger(__name__)

@on_event("sales.order_cancelled")
async def on_order_cancelled(payload: dict, metadata: dict):
    """
    Registra auditoría cuando una orden es cancelada.
    """
    actor_uuid = metadata.get("actor_uuid") or "system"
    actor_name = payload.get("actor_name") or "Unknown (EDA)"
    
    async with async_session_maker() as session:
        try:
            log = AuditLog(
                category=AuditCategory.SALES,
                action="ORDER_CANCELLED",
                reason=payload.get("reason"),
                actor_uuid=actor_uuid,
                actor_name=actor_name,
                target_id=str(payload.get("order_id")),
                target_type="order"
            )
            session.add(log)
            await session.commit()
            logger.info(f"📝 Auditoría: Orden {payload.get('order_id')} cancelada por {actor_name}")
        except Exception as e:
            logger.error(f"❌ Error en auditoría sales.order_cancelled: {e}")

@on_event("inventory.stock_adjusted")
async def on_stock_adjusted(payload: dict, metadata: dict):
    """
    Registra auditoría cuando se ajusta el stock de un ingrediente.
    """
    actor_uuid = metadata.get("actor_uuid") or "system"
    actor_name = payload.get("actor_name") or "system"
    
    async with async_session_maker() as session:
        try:
            log = AuditLog(
                category=AuditCategory.INVENTORY,
                action=f"INV_{payload.get('reason')}",
                reason=payload.get("note"),
                actor_uuid=actor_uuid,
                actor_name=actor_name,
                target_id=str(payload.get("ingredient_id")),
                target_type="ingredient",
                changes_json=json.dumps({
                    "ingredient": payload.get("ingredient_name"),
                    "old_stock": payload.get("old_stock"),
                    "new_stock": payload.get("new_stock"),
                    "delta": payload.get("delta")
                })
            )
            session.add(log)
            await session.commit()
            logger.info(f"📝 Auditoría: Inventario {payload.get('ingredient_name')} ajustado por {actor_name}")
        except Exception as e:
            logger.error(f"❌ Error en auditoría inventory.stock_adjusted: {e}")

@on_event("auth.user_login")
async def on_user_login(payload: dict, metadata: dict):
    """
    Registra auditoría de inicio de sesión.
    """
    async with async_session_maker() as session:
        try:
            log = AuditLog(
                category=AuditCategory.SECURITY,
                action="USER_LOGIN",
                actor_uuid=payload.get("user_id"),
                actor_name=payload.get("email"),
                target_id=payload.get("user_id"),
                target_type="user"
            )
            session.add(log)
            await session.commit()
            logger.info(f"📝 Auditoría: Login exitoso de {payload.get('email')}")
        except Exception as e:
            logger.error(f"❌ Error en auditoría auth.user_login: {e}")

@on_event("auth.user_registered")
async def on_user_registered(payload: dict, metadata: dict):
    """
    Registra auditoría de nuevo usuario.
    """
    async with async_session_maker() as session:
        try:
            log = AuditLog(
                category=AuditCategory.SECURITY,
                action="USER_REGISTERED",
                actor_uuid=payload.get("user_id"),
                actor_name=payload.get("email"),
                target_id=payload.get("user_id"),
                target_type="user"
            )
            session.add(log)
            await session.commit()
            logger.info(f"📝 Auditoría: Usuario {payload.get('email')} registrado")
        except Exception as e:
            logger.error(f"❌ Error en auditoría auth.user_registered: {e}")

@on_event("sales.item_cancelled")
async def on_item_cancelled(payload: dict, metadata: dict):
    """
    Registra auditoría cuando un ítem individual es cancelado.
    """
    actor_uuid = metadata.get("actor_uuid") or "system"
    actor_name = payload.get("actor_name") or "Unknown (EDA)"
    
    async with async_session_maker() as session:
        try:
            log = AuditLog(
                category=AuditCategory.SALES,
                action="ITEM_CANCELLED",
                reason=payload.get("reason"),
                actor_uuid=actor_uuid,
                actor_name=actor_name,
                target_id=str(payload.get("item_id")),
                target_type="order_item",
                changes_json=json.dumps({"order_id": payload.get("order_id")})
            )
            session.add(log)
            await session.commit()
            logger.info(f"📝 Auditoría: Ítem {payload.get('item_id')} de orden {payload.get('order_id')} cancelado")
        except Exception as e:
            logger.error(f"❌ Error en auditoría sales.item_cancelled: {e}")

@on_event("sales.order_split")
async def on_order_split(payload: dict, metadata: dict):
    """
    Registra auditoría cuando una orden se divide.
    """
    actor_uuid = metadata.get("actor_uuid") or "system"
    actor_name = payload.get("actor_name") or "Unknown (EDA)"
    
    async with async_session_maker() as session:
        try:
            log = AuditLog(
                category=AuditCategory.SALES,
                action="ORDER_SPLIT",
                reason="División de cuenta por productos",
                actor_uuid=actor_uuid,
                actor_name=actor_name,
                target_id=str(payload.get("original_order_id")),
                target_type="order",
                changes_json=json.dumps({
                    "new_order_id": payload.get("new_order_id"),
                    "items_split": payload.get("items_split")
                })
            )
            session.add(log)
            await session.commit()
            logger.info(f"📝 Auditoría: Orden {payload.get('original_order_id')} dividida -> {payload.get('new_order_id')}")
        except Exception as e:
            logger.error(f"❌ Error en auditoría sales.order_split: {e}")
