import json
import time
import network
import socket
import struct
import random

class BlackshotClient:
    def __init__(self, host, port, token, table_id=None):
        self.host = host
        self.port = port
        self.token = token
        self.table_id = table_id
        self.sock = None
        self.is_connected = False
        self.on_ready_callback = None
        self.on_msg_callback = None

    def connect_wifi(self, ssid, password):
        """Conecta al WiFi si no está conectado."""
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        if not wlan.isconnected():
            print(f"Connecting to WiFi {ssid}...")
            wlan.connect(ssid, password)
            while not wlan.isconnected():
                time.sleep(1)
        print("WiFi Connected!", wlan.ifconfig())

    def connect_ws(self):
        """Implementación minimalista de cliente WebSocket."""
        try:
            path = f"/api/v1/pos/ws/iot?token={self.token}"
            addr = socket.getaddrinfo(self.host, self.port)[0][-1]
            self.sock = socket.socket()
            self.sock.connect(addr)
            
            # HTTP Upgrade Request
            headers = [
                f"GET {path} HTTP/1.1",
                f"Host: {self.host}",
                "Upgrade: websocket",
                "Connection: Upgrade",
                "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==",
                "Sec-WebSocket-Version: 13",
                "\r\n"
            ]
            self.sock.write("\r\n".join(headers).encode())
            
            # Skip HTTP response headers
            while True:
                line = self.sock.readline()
                if not line or line == b"\r\n":
                    break
            
            self.is_connected = True
            print("WS Connected to Blackshot!")
            return True
        except Exception as e:
            print("WS Connection Failed:", e)
            return False

    def send_json(self, data):
        """Envía un payload JSON envuelto en un frame de WebSocket (Text)."""
        if not self.sock: return
        payload = json.dumps(data).encode()
        length = len(payload)
        
        # WebSocket Frame Header (Fin + Text + Masked bit set)
        header = bytearray([0x81]) 
        
        # Masking key (required for client-to-server)
        mask = bytes([random.getrandbits(8) for _ in range(4)])
        
        if length <= 125:
            header.append(length | 0x80)
        elif length <= 65535:
            header.append(126 | 0x80)
            header.extend(struct.pack(">H", length))
        else:
            header.append(127 | 0x80)
            header.extend(struct.pack(">Q", length))
            
        header.extend(mask)
        
        # Mask the payload
        masked_payload = bytearray(length)
        for i in range(length):
            masked_payload[i] = payload[i] ^ mask[i % 4]
            
        self.sock.write(header + masked_payload)

    def report_health(self, battery, rssi):
        self.send_json({
            "action": "health",
            "battery": battery,
            "rssi": rssi,
            "version": "v1.0.0-sdk"
        })

    def call_waiter(self):
        self.send_json({"action": "call_waiter"})

    def check_messages(self):
        """Escucha mensajes entrantes."""
        if not self.sock: return
        
        try:
            self.sock.setblocking(False)
            # Leer el header del frame (solo 2 bytes iniciales para saber longitud)
            h = self.sock.read(2)
            if not h: return
            
            length = h[1] & 0x7F
            if length == 126:
                length = struct.unpack(">H", self.sock.read(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self.sock.read(8))[0]
            
            # Leer payload
            payload = self.sock.read(length)
            data = json.loads(payload)
            
            # Desempaquetar formato PosSocket: {"topic": "...", "data": {...}}
            inner_data = data.get("data", {})
            ev = inner_data.get("ev")
            
            if ev == "rdy" and self.on_ready_callback:
                self.on_ready_callback(inner_data.get("msg", "Listo"))
            elif self.on_msg_callback:
                self.on_msg_callback(inner_data)
                
        except OSError: # No data available
            pass
        except Exception as e:
            print("Error checking messages:", e)
