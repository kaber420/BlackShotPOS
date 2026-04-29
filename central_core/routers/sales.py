from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from typing import Optional
from models import GlobalSale, Branch, engine
from fastapi.templating import Jinja2Templates
import os

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@router.get("/ventas", response_class=HTMLResponse)
async def sales_page(request: Request, branch_id: Optional[str] = None):
    """Historial de ventas globales con filtrado opcional."""
    with Session(engine) as session:
        statement = select(GlobalSale).options(selectinload(GlobalSale.items)).order_by(GlobalSale.created_at.desc())
        if branch_id:
            statement = statement.where(GlobalSale.branch_id == branch_id)
        sales = session.exec(statement.limit(100)).all()
        branches = session.exec(select(Branch)).all()
    
    return templates.TemplateResponse("ventas.html", {
        "request": request, 
        "sales": sales,
        "branches": branches,
        "selected_branch": branch_id,
        "active_page": "sales"
    })
