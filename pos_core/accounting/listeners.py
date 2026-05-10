import logging
from sqlalchemy import update
from pos_core.events.bus import on_event
from pos_core.database import async_session_maker
from pos_core.sales.models import PaymentMethod
from .models import Shift

logger = logging.getLogger(__name__)

@on_event("sales.payment_received")
async def on_payment_received(payload: dict, metadata: dict):
    """
    Actualiza los totales esperados del turno en tiempo real cuando se recibe un pago.
    """
    shift_id = payload.get("shift_id")
    amount = payload.get("amount", 0.0)
    method = payload.get("method")
    tip_amount = payload.get("tip_amount", 0.0)

    if not shift_id:
        logger.debug("ℹ️ Evento payment_received sin shift_id. Ignorando para contabilidad.")
        return

    logger.info(f"💰 Procesando pago de {amount} ({method}) para turno {shift_id}")

    async with async_session_maker() as session:
        try:
            # Determinamos qué columna actualizar basándonos en el método de pago
            stmt = update(Shift).where(Shift.id == shift_id)
            
            if method == PaymentMethod.CASH:
                stmt = stmt.values(expected_cash=Shift.expected_cash + amount)
            elif method == PaymentMethod.CARD:
                stmt = stmt.values(expected_card=Shift.expected_card + amount)
            elif method == PaymentMethod.TRANSFER:
                stmt = stmt.values(expected_transfer=Shift.expected_transfer + amount)
            else:
                logger.warning(f"⚠️ Método de pago desconocido: {method}")
                return

            await session.execute(stmt)
            await session.commit()
            
            logger.info(f"✅ Totales de turno {shift_id} actualizados con éxito.")

            # Broadcast para actualizar el dashboard de administración en tiempo real
            try:
                from pos_core.events.service import trigger_broadcast
                await trigger_broadcast("accounting", db=session)
            except Exception as b_err:
                logger.warning(f"⚠️ No se pudo disparar el broadcast de contabilidad: {b_err}")

        except Exception as e:
            logger.error(f"❌ Error actualizando totales de turno {shift_id}: {e}", exc_info=True)

@on_event("sales.order_cancelled")
async def on_order_cancelled(payload: dict, metadata: dict):
    """
    Maneja la cancelación de órdenes. Por ahora solo registra el evento, 
    pero podría extenderse para revertir saldos si los pagos se anulan automáticamente.
    """
    order_id = payload.get("order_id")
    shift_id = payload.get("shift_id")
    reason = payload.get("reason")
    
    logger.info(f"🚫 Orden {order_id} (Turno {shift_id}) cancelada por: {reason}")
    # TODO: Implementar lógica de reversión de pagos si el negocio lo requiere.
