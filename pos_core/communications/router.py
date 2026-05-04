import os
import uuid
import shutil
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select
from pos_core.database import get_session
from pos_core.auth.dependencies import get_current_active_user
from pos_core.auth.models import User
from pos_core.catalog.models import ProductionArea
from pos_core.events.manager import broadcaster
from .models import IntercomMessage, IntercomMessageRead, IntercomMessageAreaLink

router = APIRouter()

# Directorio para audios (ajustado para consistencia con data/img)
UPLOAD_DIR = "data/intercom"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/voice", response_model=IntercomMessageRead)
async def send_voice_message(
    audio: UploadFile = File(...),
    area_ids: Optional[str] = Form(None), # Recibido como "1,2,3"
    is_global: bool = Form(False),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_active_user)
):
    # 1. Guardar archivo
    file_extension = "webm" # Por defecto Opus en WebM
    if audio.filename and "." in audio.filename:
        file_extension = audio.filename.split(".")[-1]
    
    file_name = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, file_name)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)
    
    # 2. Crear mensaje
    new_message = IntercomMessage(
        sender_id=user.id,
        audio_path=file_name, # Guardamos solo el nombre para que la URL sea dinámica
        is_global=is_global,
        timestamp=datetime.now()
    )
    db.add(new_message)
    await db.flush() # Flush para obtener el ID sin commitear aún
    
    # 3. Vincular áreas
    parsed_area_ids = []
    if area_ids:
        try:
            parsed_area_ids = [int(aid.strip()) for aid in area_ids.split(",") if aid.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="area_ids debe ser una lista de enteros separados por comas")
            
        for area_id in parsed_area_ids:
            link = IntercomMessageAreaLink(message_id=new_message.id, area_id=area_id)
            db.add(link)
    
    await db.commit()
    await db.refresh(new_message)
    
    # 4. Broadcast real-time
    sender_name = user.email.split("@")[0].capitalize()
    broadcast_data = {
        "id": new_message.id,
        "sender_name": sender_name,
        "audio_url": f"/api/v1/pos/communications/audio/{file_name}",
        "target_areas": parsed_area_ids,
        "is_global": is_global,
        "timestamp": new_message.timestamp.isoformat()
    }
    await broadcaster.broadcast("intercom", broadcast_data)
    
    return {
        "id": new_message.id,
        "sender_id": new_message.sender_id,
        "sender_name": sender_name,
        "audio_url": f"/api/v1/pos/communications/audio/{file_name}",
        "is_global": new_message.is_global,
        "timestamp": new_message.timestamp,
        "target_areas": parsed_area_ids
    }

@router.get("/history", response_model=List[IntercomMessageRead])
async def get_history(
    limit: int = 50,
    db: AsyncSession = Depends(get_session)
):
    # Carga eficiente con emisor y áreas
    statement = (
        select(IntercomMessage)
        .options(selectinload(IntercomMessage.sender))
        .options(selectinload(IntercomMessage.target_areas))
        .order_by(IntercomMessage.timestamp.desc())
        .limit(limit)
    )
    result = await db.execute(statement)
    messages = result.scalars().all()
    
    response = []
    for msg in messages:
        sender_name = msg.sender.email.split("@")[0].capitalize() if msg.sender else "Sistema"
        area_ids = [area.id for area in msg.target_areas]
        area_names = [area.name for area in msg.target_areas]
        
        response.append({
            "id": msg.id,
            "sender_id": msg.sender_id,
            "sender_name": sender_name,
            "audio_url": f"/api/v1/pos/communications/audio/{msg.audio_path}",
            "is_global": msg.is_global,
            "timestamp": msg.timestamp,
            "target_areas": area_ids,
            "area_names": area_names
        })
    
    return response

@router.get("/audio/{filename}")
async def get_audio_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio no encontrado")
    return FileResponse(file_path, media_type="audio/webm")
