from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from .models import IoTDevice
from pos_core.sales.models import OrderStatus
import logging

logger = logging.getLogger(__name__)

async def get_device_by_token(session: AsyncSession, token: str) -> Optional[IoTDevice]:
    statement = select(IoTDevice).where(IoTDevice.token == token, IoTDevice.is_active == True)
    result = await session.execute(statement)
    return result.scalar_one_or_none()

async def update_device_last_seen(session: AsyncSession, device_id: int):
    from datetime import datetime
    device = await session.get(IoTDevice, device_id)
    if device:
        device.last_seen = datetime.utcnow()
        session.add(device)
        await session.commit()

def format_iot_payload(event: str, message: str, eta: int = 0) -> dict:
    """
    Formatea un payload minimalista para dispositivos IoT.
    Mapeo de eventos sugerido:
    - 'rdy': Ready (Listo para entrega)
    - 'prep': Preparing (En preparación)
    - 'del': Delivered (Entregado)
    - 'msg': Mensaje genérico
    """
    return {
        "ev": event,
        "msg": message,
        "eta": eta
    }

async def get_devices_by_table(session: AsyncSession, table_id: int) -> List[IoTDevice]:
    statement = select(IoTDevice).where(IoTDevice.table_id == table_id, IoTDevice.is_active == True)
    result = await session.execute(statement)
    return result.scalars().all()
