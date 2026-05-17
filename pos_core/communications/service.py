import os
import uuid
import shutil
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from pos_core.auth.models import User
from pos_core.events.manager import pos_broadcaster
from .models import IntercomMessage, IntercomMessageAreaLink

logger = logging.getLogger(__name__)

# Directorio para audios
UPLOAD_DIR = "data/intercom"
os.makedirs(UPLOAD_DIR, exist_ok=True)

async def create_voice_message(
    db: AsyncSession,
    user: User,
    audio: UploadFile,
    area_ids: Optional[List[int]] = None,
    is_global: bool = False
) -> dict:
    """
    Procesa, guarda y notifica un nuevo mensaje de voz de Intercom.
    """
    # 1. Guardar archivo físicamente
    file_extension = "webm"
    if audio.filename and "." in audio.filename:
        file_extension = audio.filename.split(".")[-1]
    
    file_name = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, file_name)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)
    except Exception as e:
        logger.error(f"❌ Error al guardar archivo de audio: {e}")
        raise RuntimeError("No se pudo guardar el archivo de audio")

    # 2. Persistencia en Base de Datos
    new_message = IntercomMessage(
        sender_id=user.id,
        audio_path=file_name,
        is_global=is_global,
        timestamp=datetime.now()
    )
    db.add(new_message)
    await db.flush()
    
    if area_ids:
        for area_id in area_ids:
            link = IntercomMessageAreaLink(message_id=new_message.id, area_id=area_id)
            db.add(link)
    
    await db.commit()
    await db.refresh(new_message)
    
    # 3. Notificación vía PubSub (Broadcast)
    sender_name = user.username.capitalize()
    audio_url = f"/api/v1/pos/communications/audio/{file_name}"
    
    broadcast_data = {
        "id": new_message.id,
        "sender_name": sender_name,
        "audio_url": audio_url,
        "target_areas": area_ids or [],
        "is_global": is_global,
        "timestamp": new_message.timestamp.isoformat()
    }
    
    await pos_broadcaster.broadcast("intercom", broadcast_data)
    
    return {
        "id": new_message.id,
        "sender_id": new_message.sender_id,
        "sender_name": sender_name,
        "audio_url": audio_url,
        "is_global": new_message.is_global,
        "timestamp": new_message.timestamp,
        "target_areas": area_ids or []
    }

async def get_intercom_history(db: AsyncSession, limit: int = 50) -> List[dict]:
    """
    Recupera el historial de mensajes formateado para el frontend.
    """
    statement = (
        select(IntercomMessage)
        .options(selectinload(IntercomMessage.sender))
        .options(selectinload(IntercomMessage.target_areas))
        .order_by(IntercomMessage.timestamp.desc())
        .limit(limit)
    )
    result = await db.execute(statement)
    messages = result.scalars().all()
    
    history = []
    for msg in messages:
        sender_name = msg.sender.username.capitalize() if msg.sender else "Sistema"
        area_ids = [area.id for area in msg.target_areas]
        area_names = [area.name for area in msg.target_areas]
        
        history.append({
            "id": msg.id,
            "sender_id": str(msg.sender_id),
            "sender_name": sender_name,
            "audio_url": f"/api/v1/pos/communications/audio/{msg.audio_path}",
            "is_global": msg.is_global,
            "timestamp": msg.timestamp.isoformat(),
            "target_areas": area_ids,
            "area_names": area_names
        })
    
    return history
