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
    Maneja la cancelación de órdenes revirtiendo los totales del turno si había pagos.
    """
    order_id = payload.get("order_id")
    
    async with async_session_maker() as session:
        try:
            from pos_core.sales.models import Order, Payment
            from sqlmodel import select
            
            # Buscamos la orden y sus pagos
            stmt = select(Order).where(Order.id == order_id)
            res = await session.execute(stmt)
            order = res.scalar_one_or_none()
            
            if not order or not order.shift_id:
                return

            pay_stmt = select(Payment).where(Payment.order_id == order_id)
            pay_res = await session.execute(pay_stmt)
            payments = pay_res.scalars().all()
            
            if not payments:
                return

            logger.info(f"🚫 Revirtiendo {len(payments)} pagos para orden cancelada {order_id}")
            
            for p in payments:
                shift_stmt = update(Shift).where(Shift.id == order.shift_id)
                if p.method == PaymentMethod.CASH:
                    shift_stmt = shift_stmt.values(expected_cash=Shift.expected_cash - p.amount)
                elif p.method == PaymentMethod.CARD:
                    shift_stmt = shift_stmt.values(expected_card=Shift.expected_card - p.amount)
                elif p.method == PaymentMethod.TRANSFER:
                    shift_stmt = shift_stmt.values(expected_transfer=Shift.expected_transfer - p.amount)
                
                await session.execute(shift_stmt)
            
            await session.commit()
            logger.info(f"✅ Totales de turno {order.shift_id} revertidos con éxito.")
            
            # Broadcast UI
            try:
                from pos_core.events.service import trigger_broadcast
                await trigger_broadcast("accounting", db=session)
            except: pass

        except Exception as e:
            logger.error(f"❌ Error revirtiendo totales por cancelación: {e}", exc_info=True)
