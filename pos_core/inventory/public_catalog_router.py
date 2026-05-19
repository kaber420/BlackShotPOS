from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pos_core.database import get_session
from pos_core.security import limiter
from pos_core.auth.dependencies import get_current_customer
from pos_core.customers.models import Customer

router = APIRouter()

@router.get("/catalog")
@limiter.limit("60/minute")
async def get_public_catalog(
    request: Request,
    current_customer: Customer = Depends(get_current_customer),
    db: AsyncSession = Depends(get_session)
):
    from pos_core.catalog.services import category_service, product_service
    
    # Asumimos que get_categories y get_products con include_inactive=False devuelven los activos
    categories = await category_service.get_categories(db)
    # Por defecto get_products no incluye inactivos
    products = await product_service.get_products(db, include_inactive=False, limit=500)
    
    # Sanitizar los productos para que NO expongan datos sensibles como recetas o stock
    safe_products = []
    for p in products:
        p_data = p.model_dump()
        # Eliminar campos confidenciales explícitamente
        p_data.pop("recipe_markdown", None)
        p_data.pop("stock", None)
        # Opcional: si hay otros datos internos en p_data, eliminarlos aquí.
        safe_products.append(p_data)
        
    # Formatear el catálogo para el frontend
    catalog_data = {
        "categories": [c.model_dump() for c in categories],
        "products": safe_products
    }
    
    return catalog_data
