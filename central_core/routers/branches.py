from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import Optional
from models import Branch, Region, engine
from manager import manager
from fastapi.templating import Jinja2Templates
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from datetime import datetime
import os

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

class BranchCreate(BaseModel):
    name: str
    base_url: str
    region_id: Optional[int] = None

@router.get("/sucursales", response_class=HTMLResponse)
async def branches_page(request: Request):
    """Página de gestión de sucursales."""
    branches = manager.list_branches()
    regions = manager.list_regions()
    users = manager.list_users()
    nats_url = os.getenv("NATS_URL", "nats://localhost:4222")
    return templates.TemplateResponse("sucursales.html", {
        "request": request, 
        "branches": branches,
        "regions": regions,
        "users": users,
        "nats_url": nats_url,
        "active_page": "branches"
    })

@router.post("/api/branches")
async def create_branch(data: BranchCreate):
    """Crea una nueva sucursal y genera sus llaves RSA."""
    private_key_obj = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_key = private_key_obj.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    public_key = private_key_obj.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')

    with Session(engine) as session:
        new_branch = Branch(
            name=data.name,
            base_url=data.base_url,
            private_key=private_key,
            public_key=public_key,
            region_id=data.region_id
        )
        session.add(new_branch)
        session.commit()
        session.refresh(new_branch)
        return new_branch

@router.get("/api/branches")
async def get_branches():
    return manager.list_branches()

@router.get("/api/branches/{branch_id}/status")
async def get_branch_status(branch_id: str):
    """Consulta el estado en vivo de una sucursal basado en su último ping."""
    with Session(engine) as session:
        branch = session.exec(select(Branch).where(Branch.id == branch_id)).first()
        if not branch:
            return {"id": branch_id, "status": "offline", "message": "Sucursal no encontrada"}
        
        if branch.last_ping:
            try:
                last_ping_dt = datetime.fromisoformat(branch.last_ping)
                diff = (datetime.utcnow() - last_ping_dt).total_seconds()
                if diff <= 90:
                    return {"id": branch_id, "status": "online"}
            except Exception:
                pass
                
        return {"id": branch_id, "status": "offline"}

@router.get("/api/branches/{branch_id}/products")
async def get_branch_products(branch_id: str):
    """Consulta los productos de una sucursal."""
    return await manager.fetch_branch_data(branch_id, "/pos/products")
