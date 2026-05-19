from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
load_dotenv()

from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pos_core.security import SecurityHeadersMiddleware, limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware
from pos_core.database import init_db
from pos_core.setup import setup_environment
from pos_core.inventory.router import router as inventory_router
from pos_core.catalog.router import router as catalog_router
from pos_core.catalog.production_router import router as production_area_router
from pos_core.media.router import router as media_router
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

# Rate Limiting Global
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- MIDDLEWARES ---
# El orden es importante. Se ejecutan en orden inverso de declaración.
# Es decir, el último en añadirse envuelve a los anteriores.

# 4. Rate Limiting (Más interno)
app.add_middleware(SlowAPIMiddleware)

# 3. Cabeceras de Seguridad
app.add_middleware(SecurityHeadersMiddleware)

# 2. Configuración de CORS
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:8000")
allowed_origins = [o.strip() for o in allowed_origins_str.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Trusted Hosts (Más externo, rechaza ataques de Host Header primero)
allowed_hosts_str = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1")
allowed_hosts = [h.strip() for h in allowed_hosts_str.split(",") if h.strip()]

app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=allowed_hosts
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
app.include_router(media_router, prefix="/api/v1/pos/media", tags=["Medios"])
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


@app.get("/api/sync/status")
async def get_sync_status():
    import json
    status_file = "data/sync_status.json"
    if os.path.exists(status_file):
        try:
            with open(status_file, "r") as f:
                return json.load(f)
        except Exception as e:
            return {"status": "offline", "error": f"Error leyendo estado: {str(e)}", "last_ping_at": None}
    return {"status": "offline", "error": "Agente de sincronización no iniciado", "last_ping_at": None}


@app.get("/")
async def root():
    return {
        "message": "Bienvenido a la API de Blackshot POS", 
        "status": "online",
        "docs": "/docs"
    }
