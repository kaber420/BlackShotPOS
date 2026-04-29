from sqlalchemy.ext.asyncio import AsyncSession
from pos_core.inventory.models import InventoryAdjustment, InventoryAdjustmentCreate, Ingredient
from pos_core.sales.models import AuditLog, AuditCategory
from pos_core.events.service import trigger_broadcast
from bs_sync.service import enqueue_event
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

async def create_adjustment(
    session: AsyncSession, 
    adjustment_data: InventoryAdjustmentCreate,
    actor_uuid: Optional[str] = None,
    actor_name: Optional[str] = None
) -> InventoryAdjustment:
    """
    Registra una merma o ajuste manual de inventario.
    Descuenta el stock del ingrediente, guarda el log y encola sincronización.
    """
    # 1. Buscar ingrediente
    ingredient = await session.get(Ingredient, adjustment_data.ingredient_id)
    if not ingredient:
        logger.error(f"❌ Error: Ingrediente {adjustment_data.ingredient_id} no encontrado")
        raise ValueError(f"Ingrediente con id {adjustment_data.ingredient_id} no encontrado")

    # 2. Restar cantidad del stock actual
    ingredient.current_stock -= adjustment_data.quantity
    session.add(ingredient)

    # 3. Guardar el registro de ajuste
    adjustment = InventoryAdjustment(
        ingredient_id=adjustment_data.ingredient_id,
        quantity=adjustment_data.quantity,
        reason=adjustment_data.reason,
        note=adjustment_data.note,
        actor_uuid=actor_uuid,
        actor_name=actor_name
    )
    session.add(adjustment)
    
    # 3.5 Registrar en la Bitácora Global de Auditoría
    audit_entry = AuditLog(
        category=AuditCategory.INVENTORY,
        action=f"ADJUSTMENT_{adjustment.reason}",
        reason=adjustment.note,
        actor_uuid=actor_uuid or "system",
        actor_name=actor_name or "system",
        target_id=str(ingredient.id),
        target_type="ingredient",
        changes_json=f'{{"ingredient": "{ingredient.name}", "qty_removed": {adjustment.quantity}}}'
    )
    session.add(audit_entry)
    
    # Comiteamos para asegurar consistencia antes de disparar eventos
    await session.commit()
    await session.refresh(adjustment)
    await session.refresh(ingredient)

    logger.info(f"✅ Ajuste registrado: {adjustment.reason} para {ingredient.name} (-{adjustment.quantity})")

    # 4. Notificar actualización de inventario vía WebSocket
    await trigger_broadcast("inventory")

    # 5. Encolar para Sincronización con Central Core
    # El agente bs_sync se encargará de empujar esto a la Central
    sync_payload = {
        "id": adjustment.id,
        "ingredient_id": adjustment.ingredient_id,
        "ingredient_name": ingredient.name,
        "quantity": adjustment.quantity,
        "reason": adjustment.reason,
        "note": adjustment.note,
        "actor_uuid": adjustment.actor_uuid,
        "actor_name": adjustment.actor_name,
        "timestamp": adjustment.timestamp.isoformat()
    }
    await enqueue_event(session, "sales.inventory_adjustment", sync_payload)
    await session.commit()

    return adjustment

async def get_adjustments(session: AsyncSession, ingredient_id: Optional[int] = None, limit: int = 100) -> List[InventoryAdjustment]:
    """Obtiene el historial reciente de ajustes, opcionalmente filtrado por ingrediente."""
    from sqlmodel import select
    stmt = select(InventoryAdjustment).order_by(InventoryAdjustment.timestamp.desc())
    
    if ingredient_id:
        stmt = stmt.where(InventoryAdjustment.ingredient_id == ingredient_id)
        
    stmt = stmt.limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()
