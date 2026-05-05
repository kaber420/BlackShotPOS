from fastapi import APIRouter, WebSocket
from pos_core.database import get_session
from .service import get_device_by_token
from .websocket_handler import handle_iot_session
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.websocket("/ws/iot")
async def iot_websocket(websocket: WebSocket):
    """
    WebSocket especializado para dispositivos IoT (ESP32).
    Se encarga de la autenticación y delega el ciclo de vida al websocket_handler.
    """
    await websocket.accept()
    
    # 1. Autenticación via token en query string
    token = websocket.query_params.get("token")
    if not token:
        await websocket.send_json({"err": "no_token"})
        await websocket.close(code=1008)
        return

    async for db in get_session():
        device = await get_device_by_token(db, token)
        if not device:
            await websocket.send_json({
                "event": "system_error", 
                "data": {"code": "AUTH_FAILED", "message": "invalid_token"}
            })
            await websocket.close(code=1008)
            return
        
        logger.info(f"🤖 Dispositivo IoT autenticado: {device.name or device.device_id} (Mesa {device.table_id})")
        
        # 2. Delegar la sesión al handler especializado
        await handle_iot_session(websocket, db, device)
        break
