# Especificación y Plan Definitivo: Portal de Clientes Desacoplado

Este plan define la arquitectura de servidores separados con inyección dinámica de seguridad para permitir un despliegue seguro, robusto y profesional.

---

## 1. Decisiones de Arquitectura

1. **Servidores Totalmente Separados:** 
   El portal de clientes (`bs_customer_portal`) corre en su propio servidor web (Caddy, Nginx o Docker) de forma independiente. El backend (`pos_core`) corre en el puerto `8400` sirviendo exclusivamente la API.
2. **Inyección Dinámica de Seguridad (IP Auto-detectada):**
   Para proteger el backend sin romper la conectividad en entornos Wi-Fi con IPs dinámicas:
   * Al arrancar, el backend detecta su IP local activa en la red.
   * **Inyección en CORS:** Se inyecta dinámicamente `http://<IP-DETECTADA>:<puertos>` en `allowed_origins` para permitir la comunicación cruzada desde el portal.
   * **Inyección en Trusted Hosts:** Se añade `<IP-DETECTADA>` a `allowed_hosts` para que el middleware de seguridad de FastAPI permita el tráfico web sin dar error 400.
3. **Configuración vía `.env` en el Portal:**
   El frontend del portal lee `PUBLIC_API_URL` desde su archivo `.env` para saber exactamente a qué IP y puerto del POS backend apuntar.

---

## 2. Cambios a Realizar

### Backend (`pos_core`)

#### [MODIFY] [main.py](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/main.py)

1. Agregar función para detectar la IP local activa en la máquina:
```python
def get_local_ip():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'
    finally:
        s.close()
```

2. Modificar la inicialización de middlewares en `main.py` para inyectar dinámicamente la IP detectada:
```python
local_ip = get_local_ip()

# Inyección en CORS
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = [o.strip() for o in allowed_origins_str.split(",") if o.strip()]
# Agregar dinámicamente la IP local en sus diferentes puertos habituales
allowed_origins.extend([
    f"http://{local_ip}",
    f"http://{local_ip}:5173",
    f"http://{local_ip}:5174",
    f"http://{local_ip}:8400"
])

# Inyección en Trusted Hosts
allowed_hosts_str = os.getenv("ALLOWED_HOSTS", "")
allowed_hosts = [h.strip() for h in allowed_hosts_str.split(",") if h.strip()]
allowed_hosts.append(local_ip)
```

---

### Portal de Clientes (`bs_customer_portal`)

#### [NEW] [.env](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/bs_customer_portal/.env)
Crear archivo de configuración local del portal apuntando al puerto de la API:
```env
PUBLIC_API_URL="http://localhost:8400"
```

#### [MODIFY] [ProductMedia.svelte](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/bs_customer_portal/src/lib/components/ProductMedia.svelte)
#### [MODIFY] [login/+page.svelte](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/bs_customer_portal/src/routes/login/+page.svelte)
#### [MODIFY] [menu/+page.svelte](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/bs_customer_portal/src/routes/menu/+page.svelte)
#### [MODIFY] [perfil/+page.svelte](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/bs_customer_portal/src/routes/perfil/+page.svelte)

Reemplazar los fetch hardcodeados de `http://localhost:8000/...` para que lean dinámicamente la variable del `.env`:
```typescript
import { PUBLIC_API_URL } from '$env/static/public';
const apiBase = PUBLIC_API_URL || '';
// fetch(`${apiBase}/api/v1/...`)
```

---

## 3. Plan de Verificación

1. Levantar el backend localmente en el puerto `8400`.
2. Verificar en la consola del servidor la IP local detectada (ej. `192.168.1.15`).
3. Levantar el portal de clientes y verificar que se conecta y consume los datos a través de la URL configurada en el `.env`.
4. Acceder al portal usando la IP local detectada y validar que CORS y Trusted Hosts permiten el tráfico correctamente gracias a la inyección dinámica.
