import asyncio
import json
import subprocess
import threading
import sys
import os
import websockets

# Configuración
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
SIMULATOR_PATH = os.path.join(ROOT_DIR, "build/BlackshotUISDK")
WS_PORT = 8765

connected_clients = set()
simulator_process = None

async def broadcast(message):
    if connected_clients:
        await asyncio.gather(*[client.send(json.dumps(message)) for client in connected_clients])

def simulator_reader():
    """Lee la salida del simulador y la envía al dashboard."""
    global simulator_process
    while True:
        if simulator_process and simulator_process.poll() is None:
            line = simulator_process.stdout.readline()
            if line:
                decoded = line.decode('utf-8').strip()
                print(f"SIM: {decoded}")
                asyncio.run_coroutine_threadsafe(
                    broadcast({"type": "LOG", "payload": decoded}), 
                    loop
                )
        else:
            break

async def handler(websocket, path):
    global simulator_process
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            data = json.loads(message)
            print(f"STUDIO: {data}")

            if data['type'] == 'ALIGN':
                # Re-posicionar ventana
                if simulator_process:
                    cmd = f"CMD:MOVE {data['x']} {data['y']}\n"
                    simulator_process.stdin.write(cmd.encode())
                    simulator_process.stdin.flush()
            
            elif data['type'] == 'COMMAND':
                if simulator_process:
                    simulator_process.stdin.write((data['command'] + "\n").encode())
                    simulator_process.stdin.flush()

    finally:
        connected_clients.remove(websocket)

async def start_simulator():
    global simulator_process
    print(f"🚀 Launching Simulator: {SIMULATOR_PATH}")
    
    # Asegurarse de que el ejecutable existe
    if not os.path.exists(SIMULATOR_PATH):
        print(f"❌ Error: {SIMULATOR_PATH} not found. Please build the project first.")
        return

    simulator_process = subprocess.Popen(
        [SIMULATOR_PATH, "--borderless"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=ROOT_DIR
    )
    
    # Hilo para leer stdout
    threading.Thread(target=simulator_reader, daemon=True).start()

async def main():
    global loop
    loop = asyncio.get_running_loop()
    
    # 1. Iniciar Simulador
    await start_simulator()
    
    # 2. Iniciar Servidor WebSocket
    print(f"🌐 Studio Bridge active on ws://localhost:{WS_PORT}")
    async with websockets.serve(handler, "localhost", WS_PORT):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        if simulator_process:
            simulator_process.terminate()
        print("\nStudio Bridge stopped.")
