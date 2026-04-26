import sys
import os
import uvicorn
import argparse
from dotenv import load_dotenv
from .setup import setup_environment, rotate_tokens

def start():
    """Extensión de CLI para Blackshot POS"""
    
    parser = argparse.ArgumentParser(description="Blackshot POS CLI")
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")

    # Comando 'run' (por defecto)
    run_parser = subparsers.add_parser("run", help="Inicia el servidor API (default)")
    run_parser.add_argument("--host", type=str, help="Host para el servidor")
    run_parser.add_argument("--port", type=int, help="Puerto para el servidor")

    # Comando 'rotate-tokens'
    rotate_parser = subparsers.add_parser("rotate-tokens", help="Rota el JWT_SECRET en el .env")

    # Parse arguments
    args = parser.parse_args()

    # Si no se especifica comando, por defecto es 'run'
    if args.command is None or args.command == "run":
        # Asegura que el entorno esté configurado antes de cargar .env
        setup_environment()
        load_dotenv()
        
        # Agrega la ruta raíz del proyecto para que pueda importar 'main.py'
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)

        host = getattr(args, "host", None) or os.getenv("HOST", "127.0.0.1")
        port = getattr(args, "port", None) or int(os.getenv("PORT", 8000))

        print(f"\n🚀 Iniciando servidor de Blackshot POS en {host}:{port}...")
        uvicorn.run("main:app", host=host, port=port, reload=True)

    elif args.command == "rotate-tokens":
        print("\n" + "!" * 50)
        print("⚠️ ADVERTENCIA: Rotar el secreto de seguridad invalidará")
        print("todas las sesiones activas de los usuarios.")
        print("!" * 50)
        confirm = input("\n¿Estás seguro de que deseas continuar? (s/N): ")
        if confirm.lower() != 's':
            print("Operación cancelada.")
            return

        rotate_tokens()

if __name__ == "__main__":
    start()
