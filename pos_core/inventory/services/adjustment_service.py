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
    Registra un movimiento de inventario (Entrada, Salida o Conteo Físico).
    Actualiza el stock, guarda el log de auditoría y encola sincronización.
    """
    # 1. Buscar ingrediente
    ingredient = await session.get(Ingredient, adjustment_data.ingredient_id)
    if not ingredient:
        logger.error(f"❌ Error: Ingrediente {adjustment_data.ingredient_id} no encontrado")
        raise ValueError(f"Ingrediente con id {adjustment_data.ingredient_id} no encontrado")

    old_stock = ingredient.current_stock
    reason = adjustment_data.reason
    
    # 2. Determinar el impacto en el stock según la razón
    delta = 0.0
    
    if reason in [AdjustmentReason.PURCHASE, AdjustmentReason.RESTOCK]:
        # ENTRADA: Sumamos la cantidad al stock actual
        delta = adjustment_data.quantity
        ingredient.current_stock += delta
    elif reason in [AdjustmentReason.PHYSICAL_COUNT, AdjustmentReason.CORRECTION]:
        # CONTEO FÍSICO: La cantidad recibida ES el nuevo stock total.
        # Calculamos el delta para el registro de auditoría.
        delta = adjustment_data.quantity - old_stock
        ingredient.current_stock = adjustment_data.quantity
    else:
        # SALIDA / MERMA: Restamos la cantidad (por defecto)
        delta = -adjustment_data.quantity
        ingredient.current_stock += delta

    session.add(ingredient)

    # 3. Guardar el registro de movimiento
    # Guardamos el delta en 'quantity' para que el historial sea consistente
    adjustment = InventoryAdjustment(
        ingredient_id=adjustment_data.ingredient_id,
        quantity=delta,
        reason=reason,
        note=adjustment_data.note,
        actor_uuid=actor_uuid,
        actor_name=actor_name
    )
    session.add(adjustment)
    
    # 3.5 Registrar en la Bitácora Global de Auditoría
    audit_entry = AuditLog(
        category=AuditCategory.INVENTORY,
        action=f"INV_{reason}",
        reason=adjustment_data.note,
        actor_uuid=actor_uuid or "system",
        actor_name=actor_name or "system",
        target_id=str(ingredient.id),
        target_type="ingredient",
        changes_json=f'{{"ingredient": "{ingredient.name}", "old_stock": {old_stock}, "new_stock": {ingredient.current_stock}, "delta": {delta}}}'
    )
    session.add(audit_entry)
    
    # Comiteamos para asegurar consistencia antes de disparar eventos
    await session.commit()
    await session.refresh(adjustment)
    await session.refresh(ingredient)

    logger.info(f"✅ Movimiento registrado: {reason} para {ingredient.name} (Δ: {delta})")

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
