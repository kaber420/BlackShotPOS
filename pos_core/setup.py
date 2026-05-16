import os
import secrets
import shutil
import socket
import sys
import subprocess
import getpass
import time
from urllib.parse import urlparse

def setup_environment():
    """
    Checks if .env exists, creates it if not, and ensures security tokens are present.
    """
    env_path = ".env"
    example_path = ".env.example"

    # 1. Create .env if missing
    if not os.path.exists(env_path):
        if os.path.exists(example_path):
            print(f"[setup] .env no encontrado. Creando desde {example_path}...")
            shutil.copy(example_path, env_path)
        else:
            print("[setup] Error: .env.example no encontrado. Creando .env básico...")
            with open(env_path, "w") as f:
                f.write('DATABASE_URL="postgresql+asyncpg://usuario:contraseña@localhost:5432/blackshot_db"\n')

    # 2. Verify and populate tokens
    _ensure_secure_tokens(env_path)

def rotate_tokens():
    """
    Explicitly regenerates the JWT_SECRET in the .env file.
    """
    env_path = ".env"
    if not os.path.exists(env_path):
        print("[setup] Error: .env no encontrado para rotar.")
        return False

    updates = {"JWT_SECRET": secrets.token_urlsafe(32)}

    _update_env_file(env_path, updates)
    print("[setup] 🔑 NUEVO JWT_SECRET generado y guardado.")
    return True

def get_local_ip():
    """Descubre la IP local de la máquina en la red LAN."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None

def check_and_prompt_ip(env_path=".env"):
    """
    Revisa si la IP local está permitida en CORS y Hosts; si no, ofrece configurarla.
    Permite autorizar la IP local, agregar manuales o mantener acceso restringido.
    """
    # Si no hay TTY (ej. ejecutando como servicio), no preguntamos
    if not sys.stdin.isatty():
        return

    local_ip = get_local_ip()
    if not local_ip or local_ip == "127.0.0.1":
        return

    if not os.path.exists(env_path):
        return

    # Leer configuración actual directamente del archivo para evitar inconsistencias de entorno
    current_hosts = ""
    current_origins = ""
    current_bind_host = "127.0.0.1"
    current_frontend_port = "80"
    current_api_port = "8000"

    with open(env_path, "r") as f:
        for line in f:
            if line.startswith("ALLOWED_HOSTS="):
                current_hosts = line.split("=", 1)[1].strip().strip('"').strip("'")
            if line.startswith("ALLOWED_ORIGINS="):
                current_origins = line.split("=", 1)[1].strip().strip('"').strip("'")
            if line.startswith("HOST="):
                current_bind_host = line.split("=", 1)[1].strip().strip('"').strip("'")
            if line.startswith("FRONTEND_PORT="):
                current_frontend_port = line.split("=", 1)[1].strip().strip('"').strip("'")
            if line.startswith("PORT="):
                current_api_port = line.split("=", 1)[1].strip().strip('"').strip("'")

    # Valores por defecto si están vacíos
    if not current_hosts: current_hosts = "localhost,127.0.0.1"
    if not current_origins: current_origins = "http://localhost:5173,http://localhost:8000"

    # Verificar si la configuración es completa (Whitelist + Binding)
    is_ip_authorized = local_ip in current_hosts and f"http://{local_ip}" in current_origins
    is_fully_configured = is_ip_authorized and current_bind_host == local_ip
    
    if not is_fully_configured:
        print(f"\n📡 [Configuración de Red] IP local detectada: {local_ip}")
        
        if is_ip_authorized and current_bind_host != local_ip:
            print(f"⚠️  Tu IP está en la Whitelist, pero el servidor solo escucha en {current_bind_host}.")
            print(f"Para que otros dispositivos entren, el servidor debe escuchar en {local_ip}.")
        else:
            print("Esta IP no está autorizada para acceso externo en la configuración actual.")
        
        try:
            print("\nOpciones:")
            print(f" [s] Autorizar IP local y activar Binding Estricto ({local_ip})")
            print(" [m] Agregar IPs o Dominios manualmente")
            print(" [n] Mantener solo acceso local (localhost)")
            
            choice = input("\nSelecciona una opción [s/m/n] (Enter para omitir): ").lower()
            
            updates = {}
            if choice == 's':
                new_hosts = f"{current_hosts},{local_ip}" if local_ip not in current_hosts else current_hosts
                new_origins = current_origins
                for p in [current_frontend_port, current_api_port]:
                    if p in ["80", "443"]:
                        o = f"http://{local_ip}" if p == "80" else f"https://{local_ip}"
                    else:
                        o = f"http://{local_ip}:{p}"
                    if o not in new_origins:
                        new_origins += f",{o}"
                
                updates = {
                    "ALLOWED_HOSTS": new_hosts,
                    "ALLOWED_ORIGINS": new_origins,
                    "HOST": local_ip
                }
                print(f"✅ Configuración actualizada: El servidor ahora escuchará en {local_ip}")
            
            elif choice == 'm':
                manual_input = input("Ingresa las IPs o dominios (ej: 192.168.1.10, mi-pos.local): ")
                extra_values = [v.strip() for v in manual_input.split(",") if v.strip()]
                
                new_hosts = current_hosts
                new_origins = current_origins
                
                for val in extra_values:
                    if val not in new_hosts:
                        new_hosts += f",{val}"
                    base_origin = f"http://{val}" if not val.startswith("http") else val
                    if ":" not in val and not val.startswith("http"):
                        for p in [current_frontend_port, current_api_port]:
                            if p in ["80", "443"]:
                                o = f"http://{val}" if p == "80" else f"https://{val}"
                            else:
                                o = f"http://{val}:{p}"
                            if o not in new_origins:
                                new_origins += f",{o}"
                    elif base_origin not in new_origins:
                        new_origins += f",{base_origin}"
                
                updates = {
                    "ALLOWED_HOSTS": new_hosts,
                    "ALLOWED_ORIGINS": new_origins,
                    "HOST": local_ip
                }
                print(f"✅ Configuración manual aplicada.")
            
            elif choice == 'n':
                print("🔒 Seguridad mantenida: Acceso restringido a localhost.")
                return

            if updates:
                _update_env_file(env_path, updates)
                for k, v in updates.items():
                    os.environ[k] = v
                    
        except (KeyboardInterrupt, EOFError):
            print("\nConfiguración omitida.")
    else:
        # Ya está configurado correctamente, solo informamos
        print(f"🚀 Red: Configuración estricta activa para {local_ip} (Whitelist + Binding)")

def _ensure_secure_tokens(env_path):
    """Checks for empty or missing tokens and populates them."""
    with open(env_path, "r") as f:
        lines = f.readlines()

    keys_to_ensure = ["JWT_SECRET", "ALLOWED_ORIGINS", "ALLOWED_HOSTS", "PUBLIC_API_URL", "HOST", "PORT", "FRONTEND_PORT"]
    current_values = {}
    
    for line in lines:
        if "=" in line and not line.strip().startswith("#"):
            parts = line.strip().split("=", 1)
            if len(parts) == 2:
                key, val = parts
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key in keys_to_ensure:
                    current_values[key] = val

    updates = {}
    for key in keys_to_ensure:
        if key == "JWT_SECRET":
            if key not in current_values or not current_values[key] or "tu-token" in current_values[key] or "identity-seed" in current_values[key] or "secret-key" in current_values[key]:
                updates[key] = secrets.token_urlsafe(32)
                print(f"[setup] 🛡️ Generando secreto de seguridad inicial ({key})")
        elif key == "ALLOWED_ORIGINS":
            if key not in current_values or not current_values[key]:
                updates[key] = "http://localhost:5173,http://localhost:8000"
                print(f"[setup] 🌐 Configurando orígenes permitidos por defecto")
        elif key == "ALLOWED_HOSTS":
            if key not in current_values or not current_values[key]:
                updates[key] = "localhost,127.0.0.1"
                print(f"[setup] 🏠 Configurando hosts permitidos por defecto")
        elif key == "PUBLIC_API_URL":
            if key not in current_values or not current_values[key]:
                updates[key] = "http://localhost:8000"
                print(f"[setup] 🔗 Configurando URL de API pública por defecto")
        elif key == "HOST":
            if key not in current_values or not current_values[key]:
                updates[key] = "127.0.0.1"
                print(f"[setup] 📍 Configurando Host de escucha por defecto (localhost)")
        elif key == "PORT":
            if key not in current_values or not current_values[key]:
                updates[key] = "8000"
                print(f"[setup] 🔌 Configurando Puerto por defecto (8000)")
        elif key == "FRONTEND_PORT":
            if key not in current_values or not current_values[key]:
                updates[key] = "80"
                print(f"[setup] 🖥️ Configurando Puerto de Frontend por defecto (80)")

    if updates:
        _update_env_file(env_path, updates)

def _update_env_file(env_path, updates):
    """Updates or adds key-value pairs in the .env file."""
    if not os.path.exists(env_path):
        return

    with open(env_path, "r") as f:
        lines = f.readlines()

    new_lines = []
    keys_handled = set()

    for line in lines:
        handled = False
        if "=" in line:
            key_part = line.split("=", 1)[0].strip()
            if key_part in updates:
                new_lines.append(f'{key_part}="{updates[key_part]}"\n')
                keys_handled.add(key_part)
                handled = True
        
        if not handled:
            new_lines.append(line)

    # Add keys that weren't in the file at all
    for key, val in updates.items():
        if key not in keys_handled:
            new_lines.append(f'{key}="{val}"\n')

    with open(env_path, "w") as f:
        f.writelines(new_lines)

def manage_systemd_services(action, service_name="all"):
    """
    Manages systemd services for Blackshot POS and Sync Agent.
    """
    user = getpass.getuser()
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    # Assume blackshot is in the same bin directory as python
    blackshot_bin = os.path.join(os.path.dirname(sys.executable), "blackshot")
    
    if not os.path.exists(blackshot_bin):
        # Fallback if not found in bin
        blackshot_bin = f"{sys.executable} -m pos_core.cli"

    services = {
        "pos": {
            "name": "blackshot-pos.service",
            "description": "Blackshot POS Service",
            "exec": f"{blackshot_bin} run",
            "after": "network.target"
        },
        "sync": {
            "name": "blackshot-sync.service",
            "description": "Blackshot Sync Agent Service",
            "exec": f"{blackshot_bin} sync",
            "after": "network.target blackshot-pos.service"
        }
    }

    selected_services = []
    if service_name == "all":
        selected_services = ["pos", "sync"]
    elif service_name in services:
        selected_services = [service_name]
    else:
        print(f"❌ Servicio desconocido: {service_name}")
        return

    if action == "install":
        for s_key in selected_services:
            s = services[s_key]
            content = f"""[Unit]
Description={s['description']}
After={s['after']}

[Service]
User={user}
WorkingDirectory={root_dir}
ExecStart={s['exec']}
EnvironmentFile={root_dir}/.env
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
            temp_file = f"/tmp/{s['name']}"
            with open(temp_file, "w") as f:
                f.write(content)
            
            print(f"📦 Instalando {s['name']}...")
            try:
                subprocess.run(["sudo", "mv", temp_file, f"/etc/systemd/system/{s['name']}"], check=True)
                subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
                subprocess.run(["sudo", "systemctl", "enable", s['name']], check=True)
                print(f"✅ {s['name']} instalado y habilitado.")
            except subprocess.CalledProcessError:
                print(f"❌ Error al instalar {s['name']}. ¿Tienes permisos de sudo?")
    
    elif action == "uninstall":
        for s_key in selected_services:
            s_name = services[s_key]["name"]
            print(f"🗑️ Desinstalando {s_name}...")
            try:
                subprocess.run(["sudo", "systemctl", "stop", s_name], check=False)
                subprocess.run(["sudo", "systemctl", "disable", s_name], check=False)
                subprocess.run(["sudo", "rm", f"/etc/systemd/system/{s_name}"], check=True)
                subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
                print(f"✅ {s_name} eliminado.")
            except subprocess.CalledProcessError:
                print(f"❌ Error al eliminar {s_name}.")

    elif action in ["start", "stop", "restart", "status", "enable", "disable"]:
        for s_key in selected_services:
            s_name = services[s_key]["name"]
            print(f"⚙️ Ejecutando {action} para {s_name}...")
            try:
                # status es el único que no necesita sudo para ver, pero mejor ser consistentes
                cmd = ["sudo", "systemctl", action, s_name]
                if action == "status":
                    # Status sin sudo para evitar el prompt si solo queremos ver
                    subprocess.run(["systemctl", action, s_name])
                else:
                    subprocess.run(cmd, check=True)
            except subprocess.CalledProcessError:
                print(f"❌ Falló {action} para {s_name}.")

def verify_db_connection(database_url=None):
    """
    Verifica si el host de la base de datos es alcanzable por red.
    """
    if not database_url:
        database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        return False, "DATABASE_URL no está configurada en el entorno."

    try:
        # Limpiar el esquema para urlparse
        clean_url = database_url.replace("postgresql+asyncpg://", "http://").replace("postgresql://", "http://")
        parsed = urlparse(clean_url)
        
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        
        # Intento de conexión por socket
        with socket.create_connection((host, port), timeout=2):
            return True, None
    except (socket.timeout, ConnectionRefusedError, socket.gaierror) as e:
        return False, f"No se pudo conectar a {host}:{port} ({type(e).__name__})"
    except Exception as e:
        return False, f"Error inesperado al verificar DB: {str(e)}"
