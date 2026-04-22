from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from omni_auth.manager import OmniAuthManager
from pos_core.database import get_session
from .manager import pos_broadcaster
import logging

logger = logging.getLogger(__name__)
_auth_manager = OmniAuthManager()

router = APIRouter()

@router.websocket("/ws/pos")
async def pos_websocket(websocket: WebSocket):
    """
    WebSocket unificado para la aplicación POS.
    Permite suscripciones a diferentes tópicos para actualizaciones en tiempo real.
    """
    await websocket.accept()
    
    # 1. Autenticación (vía query param 'token' en el handshake)
    token = websocket.query_params.get("token")
    user_info = _auth_manager.verify_token(token) if token else None
    
    if not user_info:
        await websocket.send_json({"error": "Unauthorized", "detail": "Token inválido o faltante"})
        await websocket.close(code=1008)
        return

    logger.info(f"🔌 WebSocket POS Iniciado: Usuario {user_info.get('username')}")
    subscribed_topics = set()

    try:
        # Bucle de escucha para procesar comandos del cliente
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            topic = data.get("topic")

            if action == "ping":
                # Heartbeat - solo registrar actividad para evitar el timeout
                continue

            if action == "subscribe" and topic:
                pos_broadcaster.connect(websocket, topic)
                subscribed_topics.add(topic)
                logger.info(f"📡 Usuario {user_info.get('username')} suscrito a: {topic}")

                # Enviar el estado inicial inmediatamente para que el cliente no espere al siguiente broadcast
                async for db in get_session():
                    initial_data = None
                    from pos_core.sales.schemas import OrderRead
                    if topic == "kitchen_orders":
                        from pos_core.sales.service import get_kitchen_orders
                        orders = await get_kitchen_orders(db)
                        initial_data = [OrderRead.model_validate(o).model_dump(mode="json") for o in orders]
                    elif topic == "dashboard_stats":
                        from pos_core.sales.service import get_dashboard_stats
                        initial_data = await get_dashboard_stats(db)
                    elif topic == "recent_orders":
                        from pos_core.sales.service import get_orders_json
                        orders = await get_orders_json(db)
                        initial_data = [OrderRead.model_validate(o).model_dump(mode="json") for o in orders]
                        initial_data = sorted(initial_data, key=lambda x: x["created_at"], reverse=True)
                    elif topic == "tables":
                        from pos_core.tables.service import get_tables
                        tables = await get_tables(db, include_inactive=True)
                        initial_data = [t.model_dump(mode="json") for t in tables]
                    elif topic == "admin_iot":
                        from pos_core.iot.service import get_all_devices
                        initial_data = await get_all_devices(db)
                        initial_data = [d.model_dump(mode="json") for d in initial_data]

                    if initial_data is not None:
                        await websocket.send_json({"topic": topic, "data": initial_data})
                    break
            
            elif action == "unsubscribe" and topic:
                pos_broadcaster.disconnect(websocket, topic)
                if topic in subscribed_topics:
                    subscribed_topics.remove(topic)

    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket POS: Desconexión del cliente ({user_info.get('username')})")
    except Exception as e:
        logger.error(f"❌ Error en WebSocket POS para usuario {user_info.get('username')}: {e}", exc_info=True)
    finally:
        # Limpieza final: desuscribir de todos los tópicos
        pos_broadcaster.disconnect(websocket)
