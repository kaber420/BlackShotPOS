from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select, func
from sqlalchemy.orm import selectinload
from models import GlobalSale, GlobalSaleItem, engine
from manager import manager
from fastapi.templating import Jinja2Templates
import os

router = APIRouter()

# Directorios de plantillas (relativo a este archivo o al main)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@router.get("/api/stats")
async def get_stats():
    """Calcula estadísticas globales."""
    with Session(engine) as session:
        total_sales = session.exec(select(func.sum(GlobalSale.amount))).one() or 0.0
        sales_count = session.exec(select(func.count(GlobalSale.id))).one() or 0
        
        # Calcular Top Productos
        top_products_query = select(
            GlobalSaleItem.product_name, 
            func.sum(GlobalSaleItem.quantity).label("total_quantity")
        ).group_by(GlobalSaleItem.product_name).order_by(func.sum(GlobalSaleItem.quantity).desc()).limit(5)
        
        top_products = session.exec(top_products_query).all()
        
        return {
            "total_revenue": total_sales,
            "total_sales_count": sales_count,
            "top_products": [{"name": p[0], "quantity": p[1]} for p in top_products]
        }

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Renderiza el dashboard principal con datos iniciales."""
    branches = manager.list_branches()
    regions = manager.list_regions()
    users = manager.list_users()
    with Session(engine) as session:
        last_sales = session.exec(
            select(GlobalSale)
            .options(selectinload(GlobalSale.items))
            .order_by(GlobalSale.created_at.desc())
            .limit(10)
        ).all()
    
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "branches": branches,
        "regions": regions,
        "users": users,
        "last_sales": last_sales,
        "active_page": "dashboard"
    })
