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
    """Envía un ping periódico a la Central SaaS para anunciar que el POS está en línea."""
    while True:
        try:
            js = get_js_func()
            if js:
                async with async_session_maker() as session:
                    _, current_branch_id = await get_config(session)
                
                topic = f"branches.{current_branch_id}.ping"
                payload = json.dumps({"status": "online", "timestamp": datetime.utcnow().isoformat()})
                await js.publish(topic, payload.encode())
                logger.debug(f"💓 Ping enviado a {topic}")
        except Exception as e:
            logger.error(f"⚠️ Error al enviar ping: {e}")
        
        await asyncio.sleep(60)

async def run_agent():
    print("\n" + "="*50)
    print(f"📡 BLACKSHOT POS - SYNC AGENT")
    print("="*50)
    logger.info("Iniciando Agente de Sincronización...")
    
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
                    nc = await nats.connect(nats_url)
                    js = nc.jetstream()
                    logger.info(f"✅ Conexión establecida con NATS en {nats_url}")

                await drain_queue(js)
            except Exception as e:
                logger.error(f"❌ Error en el Agente (¿NATS caído?): {e}")
                nc = None # Forzar reconexión
                js = None
            
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        ping_task.cancel()
        logger.info("👋 Agente de sincronización detenido correctamente.")

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
