import logging
import secrets
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, delete
from .models import IoTDevice

logger = logging.getLogger(__name__)

async def get_all_devices(session: AsyncSession) -> List[IoTDevice]:
    statement = select(IoTDevice)
    result = await session.execute(statement)
    return result.scalars().all()

async def get_device_by_id(session: AsyncSession, id: int) -> Optional[IoTDevice]:
    return await session.get(IoTDevice, id)

async def get_device_by_token(session: AsyncSession, token: str) -> Optional[IoTDevice]:
    statement = select(IoTDevice).where(IoTDevice.token == token, IoTDevice.is_active == True)
    result = await session.execute(statement)
    return result.scalar_one_or_none()

async def create_device(session: AsyncSession, device_data: dict) -> IoTDevice:
    # Generar un token seguro si no se proporciona
    if "token" not in device_data or not device_data["token"]:
        device_data["token"] = secrets.token_urlsafe(32)
    
    device = IoTDevice(**device_data)
    session.add(device)
    await session.commit()
    await session.refresh(device)
    return device

async def update_device(session: AsyncSession, device_id: int, update_data: dict) -> Optional[IoTDevice]:
    device = await session.get(IoTDevice, device_id)
    if not device:
        return None
    
    for key, value in update_data.items():
        if hasattr(device, key):
            setattr(device, key, value)
    
    session.add(device)
    await session.commit()
    await session.refresh(device)
    return device

async def rotate_device_token(session: AsyncSession, device_id: int) -> Optional[str]:
    device = await session.get(IoTDevice, device_id)
    if not device:
        return None
    
    new_token = secrets.token_urlsafe(32)
    device.token = new_token
    session.add(device)
    await session.commit()
    return new_token

async def delete_device(session: AsyncSession, device_id: int) -> bool:
    device = await session.get(IoTDevice, device_id)
    if not device:
        return False
    
    await session.delete(device)
    await session.commit()
    return True

async def update_device_last_seen(session: AsyncSession, device_id: int):
    device = await session.get(IoTDevice, device_id)
    if device:
        device.last_seen = datetime.now(timezone.utc)
        session.add(device)
        await session.commit()

async def update_device_health(session: AsyncSession, device_id: int, rssi: Optional[int] = None, battery: Optional[int] = None):
    device = await session.get(IoTDevice, device_id)
    if device:
        if rssi is not None: device.rssi = rssi
        if battery is not None: device.battery_level = battery
        device.last_seen = datetime.now(timezone.utc)
        session.add(device)
        await session.commit()

def format_iot_payload(event: str, message: str, eta: int = 0) -> dict:
    """Payload de comunicación nativa Blackshot IoT"""
    return {
        "event": event,
        "data": {
            "message": message,
            "eta": eta
        }
    }

async def get_devices_by_table(session: AsyncSession, table_id: int) -> List[IoTDevice]:
    statement = select(IoTDevice).where(IoTDevice.table_id == table_id, IoTDevice.is_active == True)
    result = await session.execute(statement)
    return result.scalars().all()
