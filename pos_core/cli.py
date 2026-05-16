import sys
import os
import uvicorn
import argparse
import subprocess
from dotenv import load_dotenv
from .setup import setup_environment, rotate_tokens, check_and_prompt_ip, manage_systemd_services, verify_db_connection

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

    # Comando 'sync'
    sync_parser = subparsers.add_parser("sync", help="Inicia el Agente de Sincronización y el servidor")
    sync_parser.add_argument("--host", type=str, help="Host para el servidor")
    sync_parser.add_argument("--port", type=int, help="Puerto para el servidor")
    
    # Comandos de gestión de servicios (Top-level)
    for cmd in ["install", "uninstall", "start", "stop", "restart", "status"]:
        p = subparsers.add_parser(cmd, help=f"{cmd.capitalize()} servicios de sistema")
        p.add_argument("target", nargs="?", default="all", choices=["core", "sync", "all"], 
                     help="Módulo objetivo (default: all)")

    # Parse arguments
    args = parser.parse_args()

    # Preparar entorno común
    setup_environment()
    load_dotenv()
    
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    # Verificamos la IP local para ofrecer añadirla al .env
    check_and_prompt_ip()

    def _check_db_or_prompt():
        is_ok, error = verify_db_connection()
        if not is_ok:
            print(f"\n❌ ERROR DE CONEXIÓN A BASE DE DATOS:")
            print(f"Detalle: {error}")
            
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            docker_compose_path = os.path.join(root_dir, "docker", "docker-compose.yml")
            
            if os.path.exists(docker_compose_path):
                print(f"\n💡 Se detectó una configuración de Docker.")
                try:
                    confirm = input("¿Deseas intentar levantar el contenedor de base de datos automáticamente? (s/N): ")
                    if confirm.lower() == 's':
                        print("🚀 Levantando base de datos (Postgres)...")
                        subprocess.run(["docker", "compose", "-f", docker_compose_path, "up", "-d", "db"], check=True)
                        print("⏳ Esperando a que la base de datos esté lista...")
                        import time
                        time.sleep(5)
                        
                        # Re-verify
                        is_ok, error = verify_db_connection()
                        if is_ok:
                            print("✅ Conexión establecida exitosamente.")
                            return True
                        else:
                            print(f"❌ Aún no se pudo conectar: {error}")
                            print("Es posible que la DB esté tardando en iniciar. Intenta correr el comando de nuevo en un momento.")
                            sys.exit(1)
                except (KeyboardInterrupt, EOFError):
                    print("\nOperación cancelada.")
            
            print("\nVerifica que tu base de datos esté activa y que la URL en el .env sea correcta.")
            sys.exit(1)
        return True

    # Si no se especifica comando, por defecto es 'run'
    if args.command is None or args.command == "run":
        _check_db_or_prompt()
        # Verificamos la IP local para ofrecer añadirla al .env
        check_and_prompt_ip()

        host = getattr(args, "host", None) or os.getenv("HOST", "127.0.0.1")
        
        # Medida de seguridad: No usar puertos "fantasmas"
        env_port = os.getenv("PORT")
        if not env_port and not getattr(args, "port", None):
            print("\n❌ ERROR DE CONFIGURACIÓN:")
            print("No se ha definido la variable 'PORT' en el archivo .env ni se pasó el argumento --port.")
            print("Para evitar confusiones con 'puertos fantasmas', el servidor no iniciará.")
            sys.exit(1)

        port = getattr(args, "port", None) or int(env_port)

        print(f"\n🚀 Iniciando servidor de Blackshot POS (Local) en {host}:{port}...")
        uvicorn.run("main:app", host=host, port=port, reload=True)

    elif args.command == "sync":
        _check_db_or_prompt()
        # Lanzar el agente en segundo plano
        print("\n🔄 Iniciando Agente de Sincronización en segundo plano...")
        subprocess.Popen([sys.executable, "-m", "bs_sync.agent"], cwd=root_dir)

        # Medida de seguridad: No usar puertos "fantasmas"
        env_port = os.getenv("PORT")
        if not env_port and not getattr(args, "port", None):
            print("\n❌ ERROR DE CONFIGURACIÓN (SYNC):")
            print("No se ha definido la variable 'PORT' en el archivo .env ni se pasó el argumento --port.")
            sys.exit(1)

        host = getattr(args, "host", None) or os.getenv("HOST", "127.0.0.1")
        port = getattr(args, "port", None) or int(env_port)

        # Verificamos la IP local para ofrecer añadirla al .env
        check_and_prompt_ip()

        print(f"\n🚀 Iniciando servidor de Blackshot POS (Sincronizado) en {host}:{port}...")
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

    elif args.command in ["install", "uninstall", "start", "stop", "restart", "status"]:
        # Mapeamos 'core' a 'pos' internamente para el servicio blackshot-pos
        internal_name = "pos" if args.target == "core" else args.target
        manage_systemd_services(args.command, internal_name)

if __name__ == "__main__":
    start()
