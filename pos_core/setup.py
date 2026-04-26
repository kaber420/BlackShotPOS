import os
import secrets
import shutil

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
                f.write('DATABASE_URL="sqlite+aiosqlite:///./pos_database.db"\n')

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

def _ensure_secure_tokens(env_path):
    """Checks for empty or missing tokens and populates them."""
    with open(env_path, "r") as f:
        lines = f.readlines()

    keys_to_ensure = ["JWT_SECRET"]
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
        # Generate if missing, empty, or a generic placeholder
        if key not in current_values or not current_values[key] or "tu-token" in current_values[key] or "identity-seed" in current_values[key] or "secret-key" in current_values[key]:
            updates[key] = secrets.token_urlsafe(32)
            print(f"[setup] 🛡️ Generando secreto de seguridad inicial ({key})")

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
