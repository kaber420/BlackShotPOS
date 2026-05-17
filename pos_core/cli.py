import sys
import os
import uvicorn
import argparse
import subprocess
from dotenv import load_dotenv
from .setup import setup_environment, rotate_tokens, check_and_prompt_ip, manage_systemd_services, verify_db_connection
import asyncio
import socket
import time
from urllib.parse import urlparse

async def run_sync_diagnostic():
    print("\n" + "="*60)
    print("📡 INICIANDO AUTODIAGNÓSTICO DE CONEXIÓN CON LA CENTRAL REMOTA")
    print("="*60)
    
    # 1. Obtener configuración
    from pos_core.database import async_session_maker
    from sqlmodel import select
    from pos_core.settings.models import BusinessSettings
    
    print("⚙️  Paso 1: Cargando configuración de NATS...")
    try:
        async with async_session_maker() as session:
            statement = select(BusinessSettings).where(BusinessSettings.id == 1)
            results = await session.execute(statement)
            settings = results.scalars().first()
            if not settings:
                nats_url = os.getenv("NATS_URL", "nats://localhost:4222")
                branch_id = os.getenv("BRANCH_ID", "branch_default")
            else:
                nats_url = settings.nats_url
                branch_id = settings.branch_id
        print(f"   [OK] Configuración cargada: Branch={branch_id}, NATS={nats_url}")
    except Exception as e:
        print(f"   [FAIL] Error al leer base de datos: {e}")
        return
        
    # Parse URL
    try:
        clean_url = nats_url.replace("nats://", "http://").replace("tls://", "https://").replace("ssl://", "https://")
        parsed = urlparse(clean_url)
        hostname = parsed.hostname or "localhost"
        port = parsed.port or 4222
    except Exception as e:
        print(f"   [FAIL] URL de NATS inválida '{nats_url}': {e}")
        return

    # 2. Resolución de DNS
    print(f"\n🔍 Paso 2: Resolviendo DNS para {hostname}...")
    ip = None
    try:
        t0 = time.perf_counter()
        ip = socket.gethostbyname(hostname)
        elapsed = (time.perf_counter() - t0) * 1000
        print(f"   [OK] Resuelto exitosamente a IP: {ip} (Tiempo: {elapsed:.2f}ms)")
    except Exception as e:
        print(f"   [FAIL] No se pudo resolver el nombre de host: {e}")
        print("   👉 Verifica tu conexión a internet y que el host sea correcto.")
        return

    # 3. Conectividad TCP (Socket)
    print(f"\n🔌 Paso 3: Probando conectividad TCP a {hostname}:{port}...")
    try:
        t0 = time.perf_counter()
        with socket.create_connection((hostname, port), timeout=5):
            elapsed = (time.perf_counter() - t0) * 1000
            print(f"   [OK] Puerto de red abierto. Conexión de socket exitosa (Tiempo: {elapsed:.2f}ms)")
    except Exception as e:
        print(f"   [FAIL] Conexión de red rechazada o timeout: {e}")
        print(f"   👉 Verifica que el servidor NATS esté corriendo en {hostname} en el puerto {port} y no esté bloqueado por un firewall.")
        return

    # 4. Firma Criptográfica NKEY Local
    print("\n🔐 Paso 4: Validando llaves criptográficas NKEY locales...")
    load_dotenv()
    seed = os.getenv("NATS_NKEY_SEED")
    public = os.getenv("NATS_NKEY_PUBLIC")
    if not seed:
        print("   [INFO] NATS_NKEY_SEED no está configurado en .env (Se intentará conexión anónima si es soportada)")
    else:
        try:
            import nkeys
            kp = nkeys.from_seed(seed.encode())
            test_challenge = b"blackshot_diagnostic_challenge"
            signature = kp.sign(test_challenge)
            if kp.verify(test_challenge, signature):
                print(f"   [OK] Criptografía Ed25519 validada con éxito.")
                print(f"   [OK] Seed local correcta. Public ID: {kp.public_key.decode()}")
            else:
                print("   [FAIL] La verificación de firma falló de manera inesperada.")
                return
        except Exception as e:
            print(f"   [FAIL] Error al validar firma criptográfica con nkeys: {e}")
            print("   👉 Genera un nuevo par de llaves ejecutando 'blackshot security generate-keys'.")
            return

    # 5. Conexión Completa NATS y Handshake TLS
    print(f"\n🤝 Paso 5: Realizando handshake NATS completo...")
    try:
        import nats
        import ssl
        
        connect_opts = {
            "servers": [nats_url],
            "connect_timeout": 5
        }
        
        if seed:
            import nkeys
            kp = nkeys.from_seed(seed.encode())
            async def signature_cb(nonce):
                return kp.sign(nonce)
            connect_opts["nkey"] = kp.public_key.decode()
            connect_opts["signature_cb"] = signature_cb
            
        if nats_url.startswith("tls://") or nats_url.startswith("ssl://"):
            connect_opts["tls"] = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
            print("   [INFO] Utilizando cifrado de transporte seguro TLS/SSL...")
            
        t0 = time.perf_counter()
        nc = nats.NATS()
        await nc.connect(**connect_opts)
        elapsed = (time.perf_counter() - t0) * 1000
        
        print(f"   [OK] Conexión establecida y autenticada con éxito!")
        print(f"   [OK] Handshake TLS y autenticación completados.")
        print(f"   📈 Latencia de conexión (RTT): {elapsed:.2f}ms")
        
        await nc.close()
    except Exception as e:
        print(f"   [FAIL] Falló el handshake con la Central Remota: {e}")
        print("   👉 Asegúrate de haber registrado el Public ID de esta sucursal en la Central y que la Central admita TLS/NKEY.")
        return

    print("\n" + "="*60)
    print("🎉 AUTODIAGNÓSTICO EXITOSO: ¡La sucursal está lista para operar de forma segura!")
    print("="*60 + "\n")

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
    sync_parser = subparsers.add_parser("sync", help="Inicia el Agente de Sincronización y el servidor o realiza diagnósticos")
    sync_parser.add_argument("action", nargs="?", default="run", choices=["run", "test"], help="Acción a realizar: run (iniciar agente y api) o test (diagnóstico)")
    sync_parser.add_argument("--host", type=str, help="Host para el servidor")
    sync_parser.add_argument("--port", type=int, help="Puerto para el servidor")

    # Comando 'security'
    security_parser = subparsers.add_parser("security", help="Gestión de llaves de seguridad y criptografía")
    security_subparsers = security_parser.add_subparsers(dest="security_command", help="Comandos de seguridad")
    security_subparsers.add_parser("generate-keys", help="Genera y configura un nuevo par de llaves Ed25519")
    security_subparsers.add_parser("show-id", help="Muestra el Public ID de la sucursal para registrar en la Central")
    
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
        action = getattr(args, "action", "run") or "run"
        if action == "test":
            _check_db_or_prompt()
            import asyncio
            asyncio.run(run_sync_diagnostic())
            return

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

    elif args.command == "security":
        if args.security_command == "generate-keys":
            # Check if keys already exist
            load_dotenv()
            existing_seed = os.getenv("NATS_NKEY_SEED")
            existing_public = os.getenv("NATS_NKEY_PUBLIC")
            if existing_seed or existing_public:
                print("\n" + "!" * 50)
                print("⚠️ ADVERTENCIA: Ya existe un par de llaves en el .env.")
                print("Generar nuevas llaves sobrescribirá las anteriores y requerirá")
                print("volver a registrar el nuevo Public ID en la Central Remota.")
                print("!" * 50)
                confirm = input("\n¿Deseas continuar y generar nuevas llaves? (s/N): ")
                if confirm.lower() != 's':
                    print("Operación cancelada.")
                    return
            
            print("\n🔐 Generando nuevo par de claves Ed25519...")
            from .security import generate_nkey_pair
            from .setup import _update_env_file
            
            seed, public = generate_nkey_pair()
            
            env_path = ".env"
            updates = {
                "NATS_NKEY_SEED": seed,
                "NATS_NKEY_PUBLIC": public
            }
            _update_env_file(env_path, updates)
            print("✅ Claves criptográficas generadas de forma atómica y guardadas en .env.")
            print(f"🔑 Public ID: {public}")
            print("\n👉 Recuerda registrar este Public ID en la Central Remota.")
            
        elif args.security_command == "show-id":
            load_dotenv()
            public = os.getenv("NATS_NKEY_PUBLIC")
            if not public:
                print("\n❌ ERROR: No se encontró NATS_NKEY_PUBLIC en el archivo .env.")
                print("Por favor, ejecuta 'blackshot security generate-keys' primero.")
            else:
                print("\n" + "="*60)
                print("🔑 PUBLIC ID DE LA SUCURSAL (NKEY)")
                print("="*60)
                print(f" {public}")
                print("="*60)
                print("Copia este ID y regístralo en la Central Remota para autorizar")
                print("la sincronización segura de esta sucursal.")
                print("="*60 + "\n")
        else:
            print("Uso: blackshot security [generate-keys | show-id]")

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
