import sys
import os
import uvicorn
import argparse
import subprocess
from dotenv import load_dotenv

def start():
    """CLI para Blackshot Central"""
    
    parser = argparse.ArgumentParser(description="Blackshot Central CLI")
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")

    # Comando 'run'
    run_parser = subparsers.add_parser("run", help="Inicia la Central y el Consumidor de Eventos")
    run_parser.add_argument("--host", type=str, default="127.0.0.1", help="Host para el servidor")
    run_parser.add_argument("--port", type=int, default=8001, help="Puerto para el servidor")
    run_parser.add_argument("--no-events", action="store_true", help="Inicia solo la API sin el consumidor de eventos")

    # Parse arguments
    args = parser.parse_args()

    if args.command is None:
        print("\n⚠️  No se especificó ningún comando.")
        parser.print_help()
        sys.exit(1)

    if args.command == "run":
        load_dotenv()
        
        # Filtro para silenciar el ruido de CancelledError al apagar el servidor
        import logging
        class ShutdownFilter(logging.Filter):
            def filter(self, record):
                # Silenciar errores de cancelación durante el shutdown
                if record.exc_info and isinstance(record.exc_info[1], asyncio.CancelledError):
                    return False
                if "timeout graceful shutdown exceeded" in record.getMessage():
                    return False
                return True
        
        logging.getLogger("uvicorn.error").addFilter(ShutdownFilter())
        
        # Ruta del proyecto (el directorio donde está este archivo)
        project_dir = os.path.dirname(os.path.abspath(__file__))
        if project_dir not in sys.path:
            sys.path.insert(0, project_dir)

        # Lanzar consumidor de eventos en segundo plano
        if not args.no_events:
            print("📥 Iniciando Central Event Consumer (NATS) en segundo plano...")
            # Usamos el nombre del módulo relativo al project_dir
            subprocess.Popen([sys.executable, "-m", "event_consumer"], cwd=project_dir)

        print(f"\n🌐 Iniciando Central en {args.host}:{args.port}...")
        # Al estar en el project_dir, el módulo es simplemente 'main'
        uvicorn.run("main:app", host=args.host, port=args.port, reload=True, timeout_graceful_shutdown=2)

if __name__ == "__main__":
    import asyncio # Necesario para el isinstance del filtro
    start()
