from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
import os
import uuid
import shutil

from pos_core.auth.dependencies import require_role

router = APIRouter()

@router.post("/upload", dependencies=[Depends(require_role("admin"))])
async def upload_image(file: UploadFile = File(...)):
    """Sube una imagen al servidor y retorna su URL relativa."""
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".webm"]:
        raise HTTPException(status_code=400, detail="Formato de imagen no permitido")
    
    filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join("data/img", filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"url": f"/uploads/{filename}", "filename": filename}

@router.delete("/upload/{filename}", dependencies=[Depends(require_role("admin"))])
async def delete_image(filename: str):
    """Elimina un archivo del servidor."""
    file_path = os.path.join("data/img", filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"detail": "Archivo eliminado"}
    raise HTTPException(status_code=404, detail="Archivo no encontrado")
