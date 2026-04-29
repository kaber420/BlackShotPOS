from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlmodel import Session
from pydantic import BaseModel
from models import User, engine
from manager import manager
from fastapi.templating import Jinja2Templates
import os

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

class UserCreate(BaseModel):
    email: str
    full_name: str
    password: str
    role: str

@router.get("/usuarios", response_class=HTMLResponse)
async def users_page(request: Request):
    """Página de gestión de usuarios y gerentes."""
    users = manager.list_users()
    return templates.TemplateResponse("usuarios.html", {
        "request": request, 
        "users": users,
        "active_page": "users"
    })

@router.post("/api/users")
async def create_user(data: UserCreate):
    # En un sistema real usaríamos passlib para hashear
    hashed = f"hash_{data.password}" 
    with Session(engine) as session:
        new_user = User(
            email=data.email,
            full_name=data.full_name,
            hashed_password=hashed,
            role=data.role
        )
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        return new_user
