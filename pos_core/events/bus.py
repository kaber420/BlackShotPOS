import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Awaitable

logger = logging.getLogger(__name__)

# Tipo para el manejador de eventos: una función asíncrona que recibe payload y metadatos
EventHandler = Callable[[Dict[str, Any], Dict[str, Any]], Awaitable[None]]

class InternalEventBus:
    """
    Bus de eventos interno para comunicación desacoplada entre módulos.
    Permite emitir eventos que serán procesados por múltiples suscriptores de forma asíncrona.
    """

    def __init__(self):
        # Mapeo de tópico -> lista de manejadores
        self._subscribers: Dict[str, List[EventHandler]] = {}

    def subscribe(self, topic: str, handler: EventHandler):
        """Registra un suscriptor para un tópico específico."""
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        if handler not in self._subscribers[topic]:
            self._subscribers[topic].append(handler)
            logger.debug(f"🔔 Suscrito handler '{handler.__name__}' al tópico '{topic}'")

    async def publish(self, topic: str, payload: Dict[str, Any], actor_uuid: Optional[str] = None):
        """
        Publica un evento. Los suscriptores se ejecutan en tareas de fondo.
        """
        if topic not in self._subscribers or not self._subscribers[topic]:
            logger.debug(f"ℹ️ No hay suscriptores para el tópico: {topic}")
            return

        # Construir metadatos estándar según arquitectura
        metadata = {
            "event_id": str(uuid.uuid4()),
            "topic": topic,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor_uuid": actor_uuid
        }

        logger.info(f"📤 Publicando evento '{topic}' (ID: {metadata['event_id']}) a {len(self._subscribers[topic])} suscriptores")
 
        # Disparar cada suscriptor en una tarea independiente
        for handler in self._subscribers[topic]:
            asyncio.create_task(self._safe_execute(handler, topic, payload, metadata))


    async def _safe_execute(self, handler: EventHandler, topic: str, payload: Dict[str, Any], metadata: Dict[str, Any]):
        """Ejecuta un handler capturando errores para no romper el bus."""
        try:
            await handler(payload, metadata)
        except Exception as e:
            logger.error(
                f"❌ Error en listener '{handler.__name__}' para tópico '{topic}': {e}", 
                exc_info=True
            )

# Instancia global (Singleton)
event_bus = InternalEventBus()

def on_event(topic: str):
    """
    Decorador para registrar automáticamente un listener en el event_bus.
    Uso:
        @on_event("sales.order_created")
        async def handle_order(payload, metadata):
            ...
    """
    def decorator(func: EventHandler):
        event_bus.subscribe(topic, func)
        return func
    return decorator
