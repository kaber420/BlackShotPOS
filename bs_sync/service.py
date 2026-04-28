from sqlalchemy.ext.asyncio import AsyncSession
from bs_sync.models import SyncEvent, SyncStatus
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

async def enqueue_event(session: AsyncSession, topic: str, payload: Any):
    """
    Encola un evento en la tabla SyncEvent de forma atómica.
    Debe ser llamado dentro de una transacción activa.
    """
    try:
        # Convertir payload a JSON string si no lo es
        if not isinstance(payload, str):
            payload_str = json.dumps(payload, default=str)
        else:
            payload_str = payload

        event = SyncEvent(
            topic=topic,
            payload=payload_str,
            status=SyncStatus.PENDING
        )
        
        session.add(event)
        logger.info(f"📝 Evento encolado: {topic}")
        return event
    except Exception as e:
        logger.error(f"❌ Error al encolar evento {topic}: {e}")
        # No relanzamos para no romper la transacción principal si la sincronización no es crítica,
        # pero en el Outbox Pattern usualmente QUEREMOS que falle si no se puede encolar.
        raise e
