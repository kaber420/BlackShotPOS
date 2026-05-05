import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from pos_core.database import get_session
from pos_core.auth.dependencies import get_current_active_user
from pos_core.auth.models import User
from .models import IntercomMessageRead
from .service import create_voice_message, get_intercom_history, UPLOAD_DIR

router = APIRouter()

@router.post("/voice", response_model=IntercomMessageRead)
async def send_voice_message(
    audio: UploadFile = File(...),
    area_ids: Optional[str] = Form(None), # Recibido como "1,2,3"
    is_global: bool = Form(False),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_active_user)
):
    """
    Endpoint para enviar mensajes de voz. Delega toda la lógica al servicio.
    """
    parsed_area_ids = []
    if area_ids:
        try:
            parsed_area_ids = [int(aid.strip()) for aid in area_ids.split(",") if aid.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="area_ids debe ser una lista de enteros separados por comas")
            
    try:
        return await create_voice_message(
            db=db,
            user=user,
            audio=audio,
            area_ids=parsed_area_ids,
            is_global=is_global
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history", response_model=List[IntercomMessageRead])
async def list_intercom_history(
    limit: int = 50,
    db: AsyncSession = Depends(get_session)
):
    """
    Lista el historial reciente de mensajes de intercomunicación.
    """
    return await get_intercom_history(db, limit)

@router.get("/audio/{filename}")
async def get_audio_file(filename: str):
    """
    Sirve los archivos de audio estáticos del intercom.
    """
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio no encontrado")
    return FileResponse(file_path, media_type="audio/webm")
