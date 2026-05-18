import asyncio
import nats
import json
import logging
import os
from datetime import datetime
from dotenv import load_dotenv
from sqlmodel import select
from nats.js.errors import BadRequestError

from bs_sync.models import SyncEvent, SyncStatus
from pos_core.database import async_session_maker
from pos_core.settings.models import BusinessSettings

load_dotenv()

# Silenciar logs internos de NATS para una terminal limpia
logging.getLogger("nats").setLevel(logging.CRITICAL)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("nats-agent")

def update_sync_status(status: str, last_ping_at: str = None, error: str = None):
    try:
        os.makedirs("data", exist_ok=True)
        status_file = "data/sync_status.json"
        
        # Leer existente para preservar last_ping_at si no se provee
        data = {"status": "offline", "last_ping_at": None, "error": None}
        if os.path.exists(status_file):
            try:
                with open(status_file, "r") as f:
                    data = json.load(f)
            except Exception:
                pass
                
        data["status"] = status
        if last_ping_at:
            data["last_ping_at"] = last_ping_at
        if error is not None:
            data["error"] = error
        else:
            data["error"] = None
            
        with open(status_file, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"⚠️ Error al actualizar archivo de estado de sincronización: {e}")

async def get_config(session):
    """Obtiene la configuración activa de la base de datos."""
    statement = select(BusinessSettings).where(BusinessSettings.id == 1)
    results = await session.execute(statement)
    settings = results.scalars().first()
    if not settings:
        # Valores por defecto si no hay settings
        return "nats://localhost:4222", "branch_default"
    return settings.nats_url, settings.branch_id

async def ping_loop(get_js_func):
    """Envía un ping periódico a la Central para anunciar que el POS está en línea."""
    while True:
        try:
            js = get_js_func()
            if js:
                async with async_session_maker() as session:
                    _, current_branch_id = await get_config(session)
                
                topic = f"branches.{current_branch_id}.ping"
                now_str = datetime.utcnow().isoformat()
                payload = json.dumps({"status": "online", "timestamp": now_str})
                await js.publish(topic, payload.encode())
                logger.debug(f"💓 Ping enviado a {topic}")
                update_sync_status("online", last_ping_at=now_str)
        except Exception as e:
            logger.error(f"⚠️ Error al enviar ping: {e}")
        
        await asyncio.sleep(60)

async def run_agent():
    print("\n" + "="*50)
    print(f"📡 BLACKSHOT POS - SYNC AGENT")
    print("="*50)
    logger.info("Iniciando Agente de Sincronización...")
    update_sync_status("offline", error="Iniciando agente...")
    
    # Obtener configuración inicial
    async with async_session_maker() as session:
        nats_url, branch_id = await get_config(session)
    
    logger.info(f"⚙️ Configuración cargada: Branch={branch_id}, NATS={nats_url}")
    
    nc = None
    js = None
    
    def get_js():
        return js
        
    ping_task = asyncio.create_task(ping_loop(get_js))
    
    try:
        while True:
            try:
                if not nc or not nc.is_connected:
                    connect_opts = {
                        "servers": [nats_url],
                        "connect_timeout": 10
                    }
                    
                    seed = os.getenv("NATS_NKEY_SEED")
                    if seed:
                        connect_opts["nkeys_seed_str"] = seed
                        logger.info("🔑 Autenticación NKEY habilitada para la conexión.")
                            
                    if nats_url.startswith("tls://") or nats_url.startswith("ssl://"):
                        import ssl
                        connect_opts["tls"] = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
                        logger.info("🔒 TLS/SSL activado para la conexión.")
                        
                    nc = await nats.connect(**connect_opts)
                    js = nc.jetstream()
                    logger.info(f"✅ Conexión establecida con NATS en {nats_url}")
                    update_sync_status("online")

                await drain_queue(js)
            except Exception as e:
                logger.error(f"❌ Error en el Agente (¿NATS caído?): {e}")
                update_sync_status("offline", error=str(e))
                nc = None # Forzar reconexión
                js = None
            
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        ping_task.cancel()
        logger.info("👋 Agente de sincronización detenido correctamente.")
        update_sync_status("offline", error="Agente detenido")

async def drain_queue(js):
    async with async_session_maker() as session:
        # Re-verificar branch_id por si cambió en caliente
        _, current_branch_id = await get_config(session)
        
        # Buscar eventos pendientes
        statement = select(SyncEvent).where(SyncEvent.status == SyncStatus.PENDING).limit(10)
        results = await session.execute(statement)
        events = results.scalars().all()
        
        if not events:
            return

        logger.info(f"📦 Procesando {len(events)} eventos para [{current_branch_id}]...")
        
        for event in events:
            try:
                full_topic = f"branches.{current_branch_id}.{event.topic}"
                
                # Publicar en JetStream
                await js.publish(full_topic, event.payload.encode())
                
                # Marcar como sincronizado
                event.status = SyncStatus.SYNCED
                event.synced_at = datetime.utcnow()
                session.add(event)
                logger.info(f"✅ Evento {event.id} ({event.topic}) sincronizado.")
                
            except Exception as e:
                event.attempts += 1
                event.error_message = str(e)
                if event.attempts >= 5:
                    event.status = SyncStatus.FAILED
                logger.error(f"⚠️ Error al sincronizar evento {event.id}: {e}")
                session.add(event)
        
        await session.commit()

if __name__ == "__main__":
    try:
        asyncio.run(run_agent())
    except KeyboardInterrupt:
        pass
