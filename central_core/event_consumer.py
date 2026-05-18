import asyncio
import nats
import json
import logging
import os
from dotenv import load_dotenv

load_dotenv()

# Silenciar logs internos de NATS para una terminal limpia
logging.getLogger("nats").setLevel(logging.CRITICAL)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("central-event-consumer")

NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")

async def run_consumer():
    print("\n" + "="*50)
    print("🌐 BLACKSHOT CENTRAL - EVENT CONSUMER")
    print("="*50)
    logger.info("Iniciando Consumidor de Eventos...")
    
    # Asegurar que las tablas de la base de datos central estén creadas
    try:
        create_db_and_tables()
        logger.info("✅ Tablas de la base de datos central verificadas/creadas.")
    except Exception as db_err:
        logger.error(f"⚠️ Alerta al crear tablas de base de datos: {db_err}")
    
    try:
        connect_opts = {
            "servers": [NATS_URL],
            "connect_timeout": 10
        }
        
        seed = os.getenv("NATS_NKEY_SEED")
        if seed:
            connect_opts["nkeys_seed_str"] = seed
            logger.info("🔑 Autenticación NKEY habilitada para la conexión.")
                
        if NATS_URL.startswith("tls://") or NATS_URL.startswith("ssl://"):
            import ssl
            connect_opts["tls"] = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
            logger.info("🔒 TLS/SSL activado para la conexión.")

        nc = await nats.connect(**connect_opts)
        js = nc.jetstream()
        logger.info(f"✅ Conexión establecida con NATS en {NATS_URL}")
    except Exception as e:
        print("\n" + "!"*50)
        print(f"❌ ERROR DE CONEXIÓN: El servidor NATS no está respondiendo: {e}")
        print(f"👉 Asegúrate de que NATS esté corriendo en: {NATS_URL}")
        print("   (Si usas Docker: docker run -d -p 4222:4222 nats:latest -js)")
        print("!"*50 + "\n")
        return

    # Suscribirse a todos los eventos de todas las sucursales
    # Usamos el wildcard '*' para la sucursal y '>' para todos los sub-tópicos
    subject = "branches.*.>"
    stream_name = "BRANCHES"
    
    # Intentar asegurar que el Stream exista
    try:
        await js.add_stream(name=stream_name, subjects=["branches.>"])
        logger.info(f"✅ Stream '{stream_name}' verificado/creado.")
    except Exception as e:
        logger.debug(f"Info: El stream ya podría existir: {e}")

    # Creamos una suscripción duradera (JetStream) para no perder mensajes si la Central se apaga
    try:
        sub = await js.subscribe(subject, durable="central_processor", stream=stream_name)
        logger.info(f"👂 Escuchando eventos (Durable) en: {subject}")
    except Exception as e:
        logger.warning(f"⚠️ No se pudo crear suscripción duradera: {e}")
        # Caer a suscripción normal si falla JS
        await nc.subscribe(subject, cb=handle_event)
        logger.info(f"👂 Escuchando eventos (Volátil) en: {subject}")
        # Mantener vivo el bucle ya que subscribe con callback no bloquea
        while True:
            await asyncio.sleep(1)
        return

    try:
        async for msg in sub.messages:
            await handle_event(msg)
    except asyncio.CancelledError:
        logger.info("👋 Consumidor de eventos detenido correctamente.")

async def handle_event(msg):
    subject = msg.subject
    data = json.loads(msg.data.decode())
    
    # Extraer branch_id del subject (formato: branches.ID_SUCURSAL.topic)
    parts = subject.split('.')
    branch_id = parts[1] if len(parts) > 1 else "unknown"
    topic = ".".join(parts[2:]) if len(parts) > 2 else "unknown"
    
    logger.info(f"🔔 Evento recibido de [{branch_id}] - Tópico: {topic}")
    
    if topic == "sales.payment_added":
        # Ignorar pagos parciales y registrar solo el pago final en DB
        # Si no viene la bandera, se asume True para compatibilidad directa
        if data.get('is_final_payment', True):
            process_payment(branch_id, data)
        else:
            logger.info(f"ℹ️ Pago parcial recibido de [{branch_id}]. Se omite persistencia en DB hasta el pago final.")
    elif topic == "ping":
        process_ping(branch_id, data)
    
    # Confirmar recepción (ACK) para JetStream
    try:
        await msg.ack()
    except:
        pass
    
from models import GlobalSale, GlobalSaleItem, Branch, engine, create_db_and_tables
from sqlmodel import Session, select
from datetime import datetime

def process_payment(branch_id, data):
    # Registrar el total real acumulado de la venta en lugar del monto del pago individual si es posible
    sale_amount = data.get('total_amount') or data.get('amount', 0.0)
    logger.info(f"💰 Venta procesada en la central: Sucursal={branch_id}, Monto={sale_amount}")
    
    with Session(engine) as session:
        # Obtener nombre de la sucursal
        branch = session.exec(select(Branch).where(Branch.id == branch_id)).first()
        branch_name = branch.name if branch else "Sucursal Desconocida"
        
        # Crear registro de venta global
        new_sale = GlobalSale(
            branch_id=branch_id,
            branch_name=branch_name,
            amount=sale_amount,
            items_count=data.get('items_count', 0),
            created_at=datetime.now().isoformat()
        )
        session.add(new_sale)
        session.flush() # Para obtener el ID de new_sale sin cerrar transacción
        
        # Guardar items si vienen en el evento
        items_data = data.get('items', [])
        for item in items_data:
            new_item = GlobalSaleItem(
                sale_id=new_sale.id,
                product_name=item.get('name', 'Producto Desconocido'),
                quantity=item.get('quantity', 1),
                unit_price=item.get('price', 0.0)
            )
            session.add(new_item)

        session.commit()
        logger.info(f"✅ Venta y {len(items_data)} items persistidos en DB para [{branch_name}]")

def process_ping(branch_id, data):
    with Session(engine) as session:
        branch = session.exec(select(Branch).where(Branch.id == branch_id)).first()
        if branch:
            branch.last_ping = data.get('timestamp', datetime.now().isoformat())
            session.add(branch)
            session.commit()
            logger.debug(f"💓 Ping actualizado en DB para [{branch_id}]")

if __name__ == "__main__":
    try:
        asyncio.run(run_consumer())
    except KeyboardInterrupt:
        pass # Silencioso, manejado por el log de arriba
