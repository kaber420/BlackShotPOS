from fastapi import FastAPI
from contextlib import asynccontextmanager
from pos_core.database import init_db
from pos_core.inventory.router import router as inventory_router
from pos_core.tables.router import router as tables_router
from pos_core.sales.router import router as sales_router
from omni_auth.api import router as auth_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Acciones a realizar al encender/apagar el servidor."""
    # Inicializa las tablas si no existen
    await init_db()
    yield

app = FastAPI(
    title="Blackshot POS API", 
    description="Backend para el sistema de punto de venta de café/restaurante.",
    version="0.1.0", 
    lifespan=lifespan
)

# Inclusión de rutas de inventario y mesas
app.include_router(inventory_router, prefix="/api/v1/pos", tags=["Inventario"])
app.include_router(tables_router, prefix="/api/v1/pos", tags=["Mesas"])
app.include_router(sales_router, prefix="/api/v1/pos", tags=["Ventas"])
app.include_router(auth_router, prefix="/api", tags=["Auth"])

@app.get("/")
async def root():
    return {
        "message": "Bienvenido a la API de Blackshot POS", 
        "status": "online",
        "docs": "/docs"
    }
