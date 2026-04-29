from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlmodel import Session
from pydantic import BaseModel
from typing import Optional
from models import GlobalProduct, engine
from manager import manager
from fastapi.templating import Jinja2Templates
import os

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price_suggested: float = 0.0
    category_id: Optional[int] = None
    recipe_markdown: Optional[str] = None
    calories: float = 0.0
    protein: float = 0.0
    carbs: float = 0.0
    fats: float = 0.0

@router.get("/productos", response_class=HTMLResponse)
async def products_page(request: Request):
    """Página de catálogo global de productos."""
    products = manager.list_global_products()
    categories = manager.list_categories()
    return templates.TemplateResponse("productos.html", {
        "request": request, 
        "products": products,
        "categories": categories,
        "active_page": "products"
    })

@router.post("/api/products")
async def create_product(data: ProductCreate):
    with Session(engine) as session:
        new_product = GlobalProduct(
            name=data.name, 
            description=data.description,
            price_suggested=data.price_suggested,
            category_id=data.category_id,
            recipe_markdown=data.recipe_markdown,
            calories=data.calories,
            protein=data.protein,
            carbs=data.carbs,
            fats=data.fats
        )
        session.add(new_product)
        session.commit()
        session.refresh(new_product)
        return new_product
