import os
import secrets
import shutil
import socket
import sys
import subprocess
import getpass

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
    """Revisa si la IP local está permitida en CORS y Hosts; si no, pregunta al usuario."""
    local_ip = get_local_ip()
    if not local_ip or local_ip == "127.0.0.1":
        return

    if not os.path.exists(env_path):
        return

    with open(env_path, "r") as f:
        lines = f.readlines()

    allowed_hosts = ""
    allowed_origins = ""

    for line in lines:
        if line.startswith("ALLOWED_HOSTS="):
            allowed_hosts = line.split("=", 1)[1].strip().strip('"').strip("'")
        if line.startswith("ALLOWED_ORIGINS="):
            allowed_origins = line.split("=", 1)[1].strip().strip('"').strip("'")

    needs_update = False
    if local_ip not in allowed_hosts:
        needs_update = True
    if f"http://{local_ip}" not in allowed_origins:
        needs_update = True

    if needs_update:
        print(f"\n📡 [Auto-Descubrimiento] Se ha detectado tu IP local actual: {local_ip}")
        print("Esta IP no parece estar permitida en tu configuración de seguridad (.env).")
        try:
            confirm = input("¿Deseas autorizar esta IP para que otras tablets/dispositivos puedan conectarse? (s/N): ")
            if confirm.lower() == 's':
                new_hosts = f"{allowed_hosts},{local_ip}" if allowed_hosts else local_ip
                new_origins = f"{allowed_origins},http://{local_ip}:5173,http://{local_ip}:8000" if allowed_origins else f"http://{local_ip}:5173,http://{local_ip}:8000"
                
                updates = {
                    "ALLOWED_HOSTS": new_hosts,
                    "ALLOWED_ORIGINS": new_origins
                }
                _update_env_file(env_path, updates)
                print(f"✅ IP {local_ip} agregada exitosamente.")
                
                # Update current environment variable so main.py sees it without a restart
                os.environ["ALLOWED_HOSTS"] = new_hosts
                os.environ["ALLOWED_ORIGINS"] = new_origins
        except (KeyboardInterrupt, EOFError):
            print("\nOmitido.")

def _ensure_secure_tokens(env_path):
    """Checks for empty or missing tokens and populates them."""
    with open(env_path, "r") as f:
        lines = f.readlines()

    keys_to_ensure = ["JWT_SECRET", "ALLOWED_ORIGINS", "ALLOWED_HOSTS", "PUBLIC_API_URL"]
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
