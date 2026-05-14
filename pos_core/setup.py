import os
import secrets
import shutil
import socket

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
