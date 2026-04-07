import sys
import os
import uvicorn
from dotenv import load_dotenv

def start():
    """Extensión de CLI para Blackshot POS"""
    load_dotenv()
    
    # Agrega la ruta raíz del proyecto para que pueda importar 'main.py'
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))

    print(f"\nIniciando servidor de Blackshot POS en {host}:{port}...")
    uvicorn.run("main:app", host=host, port=port, reload=True)

if __name__ == "__main__":
    start()
