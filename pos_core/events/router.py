from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pos_core.auth.backend import get_jwt_strategy
from pos_core.auth.db import get_user_db
from pos_core.database import get_session
from .manager import pos_broadcaster
from .service import get_initial_snapshot
import logging

logger = logging.getLogger(__name__)
jwt_strategy = get_jwt_strategy()

router = APIRouter()

@router.websocket("/ws/pos")
async def pos_websocket(websocket: WebSocket):
    """
    WebSocket unificado para la aplicación POS.
    Permite suscripciones a diferentes tópicos para actualizaciones en tiempo real.
    La carga de datos inicial y los broadcasts están centralizados en events/service.py.
    """
    await websocket.accept()

    # 1. Autenticación (vía query param 'token' o cookie 'bs_auth')
    token = websocket.query_params.get("token") or websocket.cookies.get("bs_auth")
    
    user = None
    if token:
        try:
            from pos_core.auth.backend import SECRET
            from pos_core.database import async_session_maker
            from pos_core.auth.models import User
            import uuid
            import jwt
            
            payload = jwt.decode(token, SECRET, algorithms=["HS256"], audience=["fastapi-users:auth"])
            user_id = payload.get("sub")
            
            if user_id:
                async with async_session_maker() as session:
                    user = await session.get(User, uuid.UUID(user_id))
        except Exception as e:
            logger.error(f"Error verificando token WS: {e}")
            user = None

    if not user:
        await websocket.send_json({"error": "Unauthorized", "detail": "Token inválido o faltante"})
        await websocket.close(code=1008)
        return

    logger.info(f"🔌 WebSocket POS Iniciado: Usuario {user.email}")
    subscribed_topics = set()

    try:
        # Bucle de escucha para procesar comandos del cliente
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            topic = data.get("topic")

            if action == "ping":
                # Heartbeat — solo registrar actividad para evitar el timeout
                continue

            if action == "subscribe" and topic:
                pos_broadcaster.connect(websocket, topic)
                subscribed_topics.add(topic)
                logger.info(f"📡 Usuario {user.email} suscrito a: {topic}")

                # Enviar el estado inicial inmediatamente para que el cliente
                # no espere al siguiente broadcast global.
                async for db in get_session():
                    initial_data = await get_initial_snapshot(topic, db)
                    if initial_data is not None:
                        await websocket.send_json({"topic": topic, "data": initial_data})
                    break

            elif action == "unsubscribe" and topic:
                pos_broadcaster.disconnect(websocket, topic)
                if topic in subscribed_topics:
                    subscribed_topics.remove(topic)

    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket POS: Desconexión del cliente ({user.email})")
    except Exception as e:
        logger.error(f"❌ Error en WebSocket POS para usuario {user.email}: {e}", exc_info=True)
    finally:
        # Limpieza final: desuscribir de todos los tópicos
        pos_broadcaster.disconnect(websocket)

