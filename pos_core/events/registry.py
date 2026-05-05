from typing import Any, Callable, Dict, Awaitable
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)

# Tipo para funciones proveedoras: reciben una sesión de BD y retornan datos serializables
TopicProvider = Callable[[AsyncSession], Awaitable[Any]]

# Registro global de tópicos
TOPIC_REGISTRY: Dict[str, TopicProvider] = {}

def register_topic_provider(topic: str, provider: TopicProvider):
    """
    Registra una función como proveedora de datos para un tópico de WebSocket.
    """
    if topic in TOPIC_REGISTRY:
        logger.warning(f"⚠️ Sobrescribiendo proveedor para el tópico: {topic}")
    
    TOPIC_REGISTRY[topic] = provider
    logger.debug(f"✅ Proveedor registrado para el tópico: {topic}")

def topic_provider(topic: str):
    """
    Decorador para registrar un proveedor de tópico automáticamente.
    """
    def decorator(func: TopicProvider):
        register_topic_provider(topic, func)
        return func
    return decorator

def get_provider(topic: str) -> TopicProvider:
    """
    Retorna el proveedor registrado para un tópico.
    """
    return TOPIC_REGISTRY.get(topic)

def list_registered_topics() -> list[str]:
    """
    Retorna la lista de tópicos registrados.
    """
    return list(TOPIC_REGISTRY.keys())
