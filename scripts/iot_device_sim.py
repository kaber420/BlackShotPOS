import asyncio
import json
import websockets
import sys
import random
from datetime import datetime

# Colores ANSI para la "Pantalla"
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"
CLEAR = "\033[H\033[J"

class IoTDeviceSimulator:
    def __init__(self, token, base_url="ws://localhost:8000"):
        self.token = token
        self.uri = f"{base_url}/api/v1/pos/ws/iot?token={token}"
        self.battery = 100
        self.is_running = True
        self.last_msg = "Esperando órdenes..."
        self.status = "Iniciando..."

    def draw_screen(self):
        """Dibuja una interfaz visual en la terminal que simula la pantalla del dispositivo."""
        print(CLEAR)
        print(f"{BOLD}╔════════════════════════════════════════════╗{RESET}")
        print(f"{BOLD}║{RESET}  {BLUE}BLACKSHOT IoT Simulator{RESET}               {BOLD}║{RESET}")
        print(f"{BOLD}╠════════════════════════════════════════════╣{RESET}")
        print(f"{BOLD}║{RESET}                                            {BOLD}║{RESET}")
        
        # Estado de salud
        bat_color = GREEN if self.battery > 20 else RED
        print(f"{BOLD}║{RESET}  BATERÍA: {bat_color}{self.battery}%{RESET}    ESTADO: {GREEN if self.is_running else RED}{self.status}{RESET}   {BOLD}║{RESET}")
        print(f"{BOLD}║{RESET}                                            {BOLD}║{RESET}")
        
        # Área de Mensaje (La "Pantalla")
        msg_centered = self.last_msg.center(40)
        print(f"{BOLD}║{RESET}  {YELLOW}{BOLD}┌──────────────────────────────────────┐{RESET}  {BOLD}║{RESET}")
        print(f"{BOLD}║{RESET}  {YELLOW}{BOLD}│{RESET}{msg_centered}{YELLOW}{BOLD}│{RESET}  {BOLD}║{RESET}")
        print(f"{BOLD}║{RESET}  {YELLOW}{BOLD}└──────────────────────────────────────┘{RESET}  {BOLD}║{RESET}")
        
        print(f"{BOLD}║{RESET}                                            {BOLD}║{RESET}")
        print(f"{BOLD}╠════════════════════════════════════════════╣{RESET}")
        print(f"{BOLD}║{RESET}  [M] Llamar Mesero   [S] Sincronizar        {BOLD}║{RESET}")
        print(f"{BOLD}║{RESET}  [B] Bajar Batería   [Q] Salir              {BOLD}║{RESET}")
        print(f"{BOLD}╚════════════════════════════════════════════╝{RESET}")
        print(f"\nÚltima actualización: {datetime.now().strftime('%H:%M:%S')}")

    async def send_health(self, ws):
        """Envía reportes de salud periódicos (heartbeat)."""
        while self.is_running:
            try:
                payload = {
                    "action": "heartbeat",
                    "data": {
                        "rssi": random.randint(-70, -40),
                        "battery": self.battery,
                        "uptime": 3600,
                        "free_heap": 250000
                    }
                }
                await ws.send(json.dumps(payload))
                await asyncio.sleep(30) # Cada 30 seg
            except Exception:
                break

    async def listen(self, ws):
        """Escucha mensajes del servidor (READY, MSG, ORDER_NEW)."""
        async for message in ws:
            try:
                data = json.loads(message)
                event = data.get("event")
                payload = data.get("data", {})
                
                if event == "rdy":
                    self.last_msg = f"🔔 {payload.get('message', '¡LISTO!')}"
                    self.draw_screen()
                elif event == "msg":
                    self.last_msg = f"📩 {payload.get('message')}"
                    self.draw_screen()
                elif event == "order_new":
                    items_count = len(payload.get("items", []))
                    self.last_msg = f"📦 Orden #{payload.get('order_id')} ({items_count} ítems)"
                    self.draw_screen()
                elif event == "config":
                    self.status = f"CONFIG: {payload.get('business_name')}"
                    self.draw_screen()
                elif event == "pong":
                    pass # Latido silencioso
            except Exception as e:
                self.status = f"Error: {str(e)[:20]}"
                self.draw_screen()

    async def handle_input(self, ws):
        """Permite interacción desde la terminal."""
        loop = asyncio.get_event_loop()
        while self.is_running:
            cmd = await loop.run_in_executor(None, lambda: sys.stdin.read(1).lower())
            if cmd == 'm':
                await ws.send(json.dumps({"action": "call_waiter"}))
                self.last_msg = "⌛ Mesero solicitado..."
                self.draw_screen()
            elif cmd == 's':
                await ws.send(json.dumps({"action": "sync_orders"}))
                self.status = "SINCRONIZANDO..."
                self.draw_screen()
            elif cmd == 'b':
                self.battery = max(0, self.battery - 10)
                await ws.send(json.dumps({
                    "action": "heartbeat", 
                    "data": {"battery": self.battery}
                }))
                self.draw_screen()
            elif cmd == 'q':
                self.is_running = False
                break

    async def run(self):
        self.draw_screen()
        try:
            async with websockets.connect(self.uri) as ws:
                self.status = "CONECTADO"
                self.draw_screen()
                
                # Ejecutar tareas en paralelo
                await asyncio.gather(
                    self.send_health(ws),
                    self.listen(ws),
                    self.handle_input(ws)
                )
        except Exception as e:
            self.status = "DESCONECTADO"
            self.last_msg = f"Error: {e}"
            self.draw_screen()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/iot_device_sim.py <TOKEN>")
        sys.exit(1)
    
    token = sys.argv[1]
    url = sys.argv[2] if len(sys.argv) > 2 else "ws://localhost:8000"
    
    sim = IoTDeviceSimulator(token, url)
    try:
        asyncio.run(sim.run())
    except KeyboardInterrupt:
        pass
