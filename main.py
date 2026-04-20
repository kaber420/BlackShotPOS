from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
from pos_core.database import init_db
from pos_core.inventory.router import router as inventory_router
from pos_core.tables.router import router as tables_router
from pos_core.sales.router import router as sales_router
from pos_core.printing.router import router as printing_router
from pos_core.sales.shifts_router import router as shifts_router
from pos_core.settings.router import router as settings_router
from pos_core.sales.analytics_router import router as analytics_router
from pos_core.sales.audits_router import router as audits_router
from pos_core.events.router import router as events_router
from pos_core.iot.router import router as iot_router
from omni_auth.api import router as auth_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Acciones a realizar al encender/apagar el servidor."""
    # Asegurar que el directorio de datos existe
    os.makedirs("data/img", exist_ok=True)
    # Inicializa las tablas si no existen
    await init_db()
    yield

app = FastAPI(
    title="Blackshot POS API", 
    description="Backend para el sistema de punto de venta de café/restaurante.",
    version="0.1.0", 
    lifespan=lifespan
)

# Montar archivos estáticos para subidas de fotos
app.mount("/uploads", StaticFiles(directory="data/img"), name="uploads")

# Inclusión de rutas de inventario y mesas
app.include_router(inventory_router, prefix="/api/v1/pos", tags=["Inventario"])
app.include_router(tables_router, prefix="/api/v1/pos", tags=["Mesas"])
app.include_router(sales_router, prefix="/api/v1/pos", tags=["Ventas"])
app.include_router(shifts_router, prefix="/api/v1/pos/shifts", tags=["Cortes de Caja"])
app.include_router(printing_router, prefix="/api/v1/pos", tags=["Impresión"])
app.include_router(settings_router, prefix="/api/v1/pos/settings", tags=["Configuración"])
app.include_router(analytics_router, prefix="/api/v1/pos/analytics", tags=["Analíticas"])
app.include_router(audits_router, prefix="/api/v1/pos", tags=["Auditoría"])
app.include_router(events_router, prefix="/api/v1/pos", tags=["Eventos"])
app.include_router(iot_router, prefix="/api/v1/pos", tags=["IoT"])
app.include_router(auth_router, prefix="/api", tags=["Auth"])

@app.get("/")
async def root():
    return {
        "message": "Bienvenido a la API de Blackshot POS", 
        "status": "online",
        "docs": "/docs"
    }
