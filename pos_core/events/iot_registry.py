from typing import Any, Callable, Dict, Awaitable
import logging

logger = logging.getLogger(__name__)

# Tipo para funciones mapeadoras de IoT: reciben el tópico original y los datos
IoTMapper = Callable[[str, Any], Awaitable[None]]

# Registro global de mapeadores IoT
IOT_MAPPER_REGISTRY: Dict[str, IoTMapper] = {}

def register_iot_mapper(topic: str, mapper: IoTMapper):
    """
    Registra una función para mapear datos de un tópico POS a comandos IoT.
    """
    IOT_MAPPER_REGISTRY[topic] = mapper
    logger.debug(f"🤖 Mapeador IoT registrado para el tópico: {topic}")

def iot_mapper(topic: str):
    """
    Decorador para registrar un mapeador IoT automáticamente.
    """
    def decorator(func: IoTMapper):
        register_iot_mapper(topic, func)
        return func
    return decorator

def get_iot_mapper(topic: str) -> IoTMapper:
    """
    Retorna el mapeador IoT registrado para un tópico.
    """
    return IOT_MAPPER_REGISTRY.get(topic)
