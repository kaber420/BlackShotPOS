from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlmodel import Session
from pydantic import BaseModel
from typing import Optional
from models import Region, engine
from manager import manager
from fastapi.templating import Jinja2Templates
import os

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

class RegionCreate(BaseModel):
    name: str
    description: Optional[str] = None

@router.get("/regiones", response_class=HTMLResponse)
async def regions_page(request: Request):
    """Página de gestión de regiones."""
    regions = manager.list_regions()
    return templates.TemplateResponse("regiones.html", {
        "request": request, 
        "regions": regions,
        "active_page": "regions"
    })

@router.post("/api/regions")
async def create_region(data: RegionCreate):
    with Session(engine) as session:
        new_region = Region(name=data.name, description=data.description)
        session.add(new_region)
        session.commit()
        session.refresh(new_region)
        return new_region
