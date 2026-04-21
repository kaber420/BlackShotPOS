from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pos_core.database import get_session
from . import service
from .models import IoTDevice
from pos_core.settings.service import get_settings
from pos_core.events.manager import iot_broadcaster
from omni_auth.security import require_permission
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter()

class IoTDeviceCreate(BaseModel):
    device_id: str
    name: Optional[str] = None
    type: str = "esp32"
    table_id: Optional[int] = None

class IoTDeviceUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    table_id: Optional[int] = None
    is_active: Optional[bool] = None

@router.get("/devices", response_model=List[IoTDevice])
async def list_devices(
    db: AsyncSession = Depends(get_session),
    user=Depends(require_permission("can_manage_iot"))
):
    """Lista todos los dispositivos IoT registrados."""
    return await service.get_all_devices(db)

@router.post("/devices", response_model=IoTDevice)
async def create_device(
    device_in: IoTDeviceCreate,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_permission("can_manage_iot"))
):
    """Registra/Provisiona un nuevo dispositivo IoT."""
    return await service.create_device(db, device_in.dict())

@router.patch("/devices/{device_id}", response_model=IoTDevice)
async def update_device(
    device_id: int,
    device_in: IoTDeviceUpdate,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_permission("can_manage_iot"))
):
    """Actualiza la configuración de un dispositivo (nombre, mesa, tipo)."""
    device = await service.update_device(db, device_id, device_in.dict(exclude_unset=True))
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    return device

@router.post("/devices/{device_id}/rotate-token")
async def rotate_token(
    device_id: int,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_permission("can_manage_iot"))
):
    """Invalida el token actual y genera uno nuevo."""
    token = await service.rotate_device_token(db, device_id)
    if not token:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    return {"token": token}

@router.delete("/devices/{device_id}")
async def delete_device(
    device_id: int,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_permission("can_manage_iot"))
):
    """Elimina físicamente un dispositivo del sistema."""
    success = await service.delete_device(db, device_id)
    if not success:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    return {"status": "success", "message": "Dispositivo eliminado"}

@router.post("/devices/sync")
async def sync_all_devices(
    db: AsyncSession = Depends(get_session),
    user=Depends(require_permission("can_manage_iot"))
):
    """
    Fuerza a todos los dispositivos conectados a actualizar su configuración
    (Nombre del negocio, etc).
    """
    try:
        settings = await get_settings(db)
        # Iterar sobre todos los tópicos de mesas que tienen conexiones activas
        count = 0
        for topic, websockets in iot_broadcaster.active_connections.items():
            if not topic.startswith("iot_table_") or not websockets:
                continue
            
            table_id = int(topic.replace("iot_table_", ""))
            
            # Nota: En un broadcast masivo, no tenemos el nombre específico del dispositivo 
            # fácilmente accesible aquí sin re-consultar cada uno. 
            # Enviamos el nombre del negocio actualizado.
            payload = {
                "event": "config",
                "data": {
                    "business_name": settings.name,
                    "table_id": table_id
                }
            }
            
            # Usamos el broadcaster para enviar a todo el tópico (mesa)
            await iot_broadcaster.broadcast(topic, payload)
            count += len(websockets)
            
        return {"status": "success", "message": f"Sincronización enviada a {count} dispositivos activos"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error durante la sincronización: {str(e)}")
