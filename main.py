from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
from pos_core.database import init_db
from pos_core.setup import setup_environment
from pos_core.inventory.router import router as inventory_router
from pos_core.catalog.router import router as catalog_router
from pos_core.catalog.production_router import router as production_area_router
from pos_core.tables.router import router as tables_router
from pos_core.sales.router import router as sales_router
from pos_core.kitchen.printing.router import router as printing_router
from pos_core.accounting.router import router as shifts_router
from pos_core.settings.router import router as settings_router
from pos_core.analytics.router import router as analytics_router
from pos_core.audit.router import router as audits_router
from pos_core.events.router import router as events_router
from pos_core.iot.router import router as iot_router
from pos_core.iot.admin_router import router as admin_iot_router
from pos_core.auth.router import auth_router, user_router
from pos_core.customers.router import router as customer_router
from pos_core.communications.router import router as communications_router
from pos_core.kitchen.router import router as kitchen_router
from pos_core.events.discovery import discover_event_providers, discover_event_listeners


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Acciones a realizar al encender/apagar el servidor."""
    # Asegura que el entorno (.env y tokens) esté listo
    setup_environment()
    # Inicializa las tablas si no existen
    await init_db()
    # Descubrimiento automático de proveedores de eventos (WebSockets)
    discover_event_providers()
    # Descubrimiento automático de suscriptores de eventos (Lógica Interna)
    discover_event_listeners()
    yield

app = FastAPI(
    title="Blackshot POS API", 
    description="Backend para el sistema de punto de venta de café/restaurante.",
    version="0.1.0", 
    lifespan=lifespan
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción deberíamos restringir esto
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Asegurar que el directorio de datos existe antes de montar
os.makedirs("data/img", exist_ok=True)

# Montar archivos estáticos para subidas de fotos
app.mount("/uploads", StaticFiles(directory="data/img"), name="uploads")

from pos_core.exceptions import BusinessLogicError

@app.exception_handler(BusinessLogicError)
async def business_logic_exception_handler(request: Request, exc: BusinessLogicError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "detail": exc.detail
        },
    )

# Inclusión de rutas por dominio
app.include_router(catalog_router, prefix="/api/v1/pos/catalog", tags=["Catálogo"])
app.include_router(production_area_router, prefix="/api/v1/pos/catalog/production", tags=["Áreas de Producción"])
app.include_router(inventory_router, prefix="/api/v1/pos/inventory", tags=["Inventario"])
app.include_router(tables_router, prefix="/api/v1/pos/tables", tags=["Mesas"])
app.include_router(sales_router, prefix="/api/v1/pos/sales", tags=["Ventas"])
app.include_router(shifts_router, prefix="/api/v1/pos/sales/shifts", tags=["Cortes de Caja"])
app.include_router(customer_router, prefix="/api/v1/pos/sales/customers", tags=["Clientes"])
app.include_router(printing_router, prefix="/api/v1/pos/system/printing", tags=["Impresión"])
app.include_router(settings_router, prefix="/api/v1/pos/system/settings", tags=["Configuración"])
app.include_router(analytics_router, prefix="/api/v1/pos/system/analytics", tags=["Analíticas"])
app.include_router(audits_router, prefix="/api/v1/pos/system/audit", tags=["Auditoría"])
app.include_router(events_router, prefix="/api/v1/pos/events", tags=["Eventos"])
app.include_router(iot_router, prefix="/api/v1/pos/iot", tags=["IoT"])
app.include_router(admin_iot_router, prefix="/api/v1/pos/admin/iot", tags=["IoT Admin"])
app.include_router(communications_router, prefix="/api/v1/pos/communications", tags=["Comunicaciones/Intercom"])
app.include_router(kitchen_router, prefix="/api/v1/pos/kitchen", tags=["Cocina"])
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(user_router, prefix="/api/users", tags=["Users"])


@app.get("/")
async def root():
    return {
        "message": "Bienvenido a la API de Blackshot POS", 
        "status": "online",
        "docs": "/docs"
    }
