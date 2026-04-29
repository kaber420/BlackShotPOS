from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import json
import asyncio

router = APIRouter()

@router.get("/api/events/feed")
async def event_feed(request: Request):
    """Transmite eventos de NATS al frontend vía SSE."""
    async def event_generator():
        nats_connection = getattr(request.app.state, "nats_connection", None)
        
        if not nats_connection:
            yield "data: {\"error\": \"NATS no conectado\"}\n\n"
            return

        # Suscribirse a eventos de ventas
        sub = await nats_connection.subscribe("branches.*.sales.payment_added")
        
        try:
            while True:
                if await request.is_disconnected():
                    break
                
                try:
                    # Esperar mensaje con un breve timeout para poder revisar desconexión
                    msg = await asyncio.wait_for(sub.messages.__anext__(), timeout=2.0)
                    
                    data = json.loads(msg.data.decode())
                    subject_parts = msg.subject.split('.')
                    data['branch_id'] = subject_parts[1]
                    
                    yield f"data: {json.dumps(data)}\n\n"
                except asyncio.TimeoutError:
                    # Comentario para mantener la conexión viva y re-evaluar is_disconnected
                    yield ": keep-alive\n\n"
                    continue
        except (asyncio.CancelledError, Exception):
            pass
        finally:
            try:
                await sub.unsubscribe()
            except:
                pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")
