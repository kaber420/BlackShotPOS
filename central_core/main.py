from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os
import nats
import asyncio
import logging
from models import create_db_and_tables
from routers import dashboard, branches, products, users, events, regions, sales

# Filtro para silenciar el ruido de CancelledError al apagar el servidor
class ShutdownFilter(logging.Filter):
    def filter(self, record):
        if record.exc_info and isinstance(record.exc_info[1], asyncio.CancelledError):
            return False
        if "timeout graceful shutdown exceeded" in record.getMessage():
            return False
        return True

logging.getLogger("uvicorn.error").addFilter(ShutdownFilter())

app = FastAPI(title="Blackshot Central Panel")

# App State para compartir conexiones
app.state.nats_connection = None

# Directorios de estáticos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

@app.on_event("startup")
async def on_startup():
    create_db_and_tables()
    try:
        app.state.nats_connection = await nats.connect(os.getenv("NATS_URL", "nats://localhost:4222"))
    except Exception as e:
        print(f"⚠️ Warning: Could not connect to NATS in API: {e}")

@app.on_event("shutdown")
async def on_shutdown():
    if app.state.nats_connection:
        await app.state.nats_connection.close()

# Incluir Routers
app.include_router(dashboard.router)
app.include_router(branches.router)
app.include_router(products.router)
app.include_router(users.router)
app.include_router(events.router)
app.include_router(regions.router)
app.include_router(sales.router)
