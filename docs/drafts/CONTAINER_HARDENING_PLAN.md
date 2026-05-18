# Plan de Endurecimiento Radical de Contenedores e Infraestructura
**Documento de Diseño / RFC**  
**Estado:** Borrador (Draft)  
**Autor:** Antigravity AI  
**Objetivo:** Reducir la superficie de ataque al mínimo absoluto en producción para el ecosistema BlackShotPOS, asumiendo un entorno hostil y la posibilidad de comprometimiento del Kernel de Linux.

---

## 1. Introducción y Filosofía de Seguridad

En un despliegue de alta seguridad en producción, la contenedorización por sí sola no constituye un límite de seguridad robusto si los contenedores se ejecutan con privilegios predeterminados. Si un atacante compromete un contenedor (por ejemplo, a través de una inyección SQL o una ejecución remota de código - RCE):
1. **Como root:** Si el proceso interno corre como `root` (UID 0), tiene acceso total a llamadas del sistema privilegiadas, facilitando la explotación de vulnerabilidades del Kernel del host para escapar del contenedor.
2. **Con herramientas del sistema:** Si el contenedor tiene shells (`sh`, `bash`), compiladores (`gcc`) o utilidades de red (`curl`, `wget`), el atacante puede descargar y compilar localmente exploits específicos para el Kernel.
3. **Con puertos expuestos públicamente:** Si servicios como PostgreSQL exponen sus puertos al mundo exterior, la base de datos se convierte en blanco directo de ataques de fuerza bruta y vulnerabilidades de día cero.

Este plan adopta una estrategia de **Defensa en Profundidad** y **Aislamiento Radical**:
* **Stateless (Frontend):** Aislamiento extremo mediante contenedores vacíos (`scratch`) con servidores estáticos nativos y eficientes en Rust (Static-Web-Server).
* **Stateful (Database):** Bloqueo total del runtime (`read-only`, `tmpfs`, `cap_drop: [ALL]`) y anulación de visibilidad pública de puertos.
* **Dynamic (Backend/Sync Agent):** Transición a usuarios no root y eliminación total de herramientas de compilación en el entorno de ejecución final usando *Multi-Stage Builds*.

---

## 2. Evaluación de Riesgos y Hallazgos Actuales

Tras auditar la base de código de BlackShotPOS, se detectaron los siguientes puntos débiles críticos:

1. **Exposición de PostgreSQL:** En el `docker-compose.yml`, el servicio `db` mapea `"5432:5432"` públicamente. En producción, esto expone la base de datos a Internet innecesariamente, ya que el backend FastAPI se comunica mediante la red interna de Docker.
2. **Backend FastAPI ejecutado como Root:** El `Dockerfile` del backend no define un usuario no root. El servidor de producción `uvicorn` corre como `root` (UID 0), lo que permite que cualquier compromiso del backend tenga control total del espacio de usuario del contenedor.
3. **Persistencia de compiladores en el Backend:** La imagen final del backend conserva `build-essential` y cabeceras de compilación necesarias para instalar `cryptography`, `asyncpg` y `escpos`, brindando al atacante herramientas de desarrollo.
4. **Nginx con shell activo en el Frontend:** La imagen `nginx:stable-alpine` del frontend, aunque es ligera, contiene un sistema operativo completo con un shell ejecutable (`/bin/sh`) y gestores de paquetes.

---

## 3. Propuesta Técnica y Configuraciones Detalladas

A continuación se presentan los archivos configurados y listos para producción para endurecer cada componente.

### A. Endurecimiento de la Base de Datos (PostgreSQL)

PostgreSQL requiere escribir datos en disco, por lo que su sistema de archivos no puede ser 100% de solo lectura de forma simple sin configuraciones adicionales. Logramos inmutabilidad total del sistema raíz redirigiendo los archivos temporales y sockets a memoria RAM (`tmpfs`), dejando el almacenamiento de datos estrictamente en el volumen persistente de Docker.

#### Medidas Aplicadas:
* **`read_only: true`:** El sistema de archivos raíz se congela. El atacante no puede inyectar scripts en `/bin`, `/usr` o `/var`.
* **`tmpfs`:** Montamos en memoria RAM `/run/postgresql` (donde PostgreSQL almacena sus archivos de sockets y bloqueo) y `/tmp` con los IDs de usuario correctos (UID/GID `70:70` correspondiente al usuario `postgres` en Alpine).
* **`cap_drop: [ALL]`:** Elimina todas las capacidades administrativas de la CPU a nivel de llamadas del kernel.
* **`security_opt: [no-new-privileges:true]`:** Impide que los procesos hijos de Postgres eleven sus privilegios mediante binarios SUID o llamadas al sistema especiales.
* **Eliminación de Mapeo de Puertos Públicos:** Se remueve la directiva `ports` y se mantiene únicamente el aislamiento interno de Docker con `expose`.

---

### B. Endurecimiento del Backend y Agente de Sincronización (FastAPI / Python)

Reestructuramos el `docker/backend/Dockerfile` para implementar un **Multi-Stage Build** (Etapas de Construcción Múltiples) para compilar las dependencias dinámicas de Python y luego transferirlas a una imagen final limpia, donde correrán bajo un usuario de sistema no privilegiado.

#### [NUEVO] Dockerfile Endurecido para el Backend (`docker/backend/Dockerfile`)

```dockerfile
# ==========================================================
# Etapa 1: Compilación de Dependencias (Builder)
# ==========================================================
FROM python:3.12-slim AS builder

WORKDIR /app

# Instalar dependencias del sistema necesarias para compilar librerías nativas
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    libusb-1.0-0-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar configuración del proyecto
COPY pyproject.toml ./

# Crear un entorno virtual aislado
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copiar el código fuente para compilar el paquete del POS
COPY . .

# Instalar dependencias en el entorno virtual
RUN pip install --no-cache-dir -e .

# ==========================================================
# Etapa 2: Imagen de Ejecución Limpia y Segura (Runner)
# ==========================================================
FROM python:3.12-slim AS runner

WORKDIR /app

# Instalar UNICAMENTE las librerías dinámicas compartidas de ejecución (ej. libusb para impresión térmica)
# Se excluyen compiladores, cabeceras de desarrollo y paquetes innecesarios
RUN apt-get update && apt-get install -y \
    libusb-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copiar el virtualenv compilado de la etapa 1
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copiar el código fuente de la aplicación
COPY . .

# Crear un usuario y grupo de sistema no privilegioso con UID explícito
# Usamos un UID alto fuera del rango estándar del sistema host (ej. 10001)
RUN groupadd -g 10001 blackshot_group && \
    useradd -r -u 10001 -g blackshot_group blackshot_user && \
    chown -R blackshot_user:blackshot_group /app

# Ejecutar el contenedor bajo el usuario no root creado
USER 10001

EXPOSE 8000

# Comando por defecto para arrancar la API
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### C. Endurecimiento del Frontend (SvelteKit)

Reemplazamos el tradicional servidor Nginx en Alpine por **Static-Web-Server (SWS)**, una utilidad escrita en Rust de alto rendimiento y enfocada en la seguridad de memoria, corriendo sobre una imagen **`scratch`** (completamente vacía, sin sistema operativo ni intérprete de comandos).

#### [NUEVO] Dockerfile Endurecido para el Frontend (`docker/frontend/Dockerfile`)

```dockerfile
# ==========================================================
# Etapa 1: Compilación de la Aplicación SvelteKit
# ==========================================================
FROM node:20-alpine AS build-frontend
WORKDIR /app

# Habilitar pnpm estrictamente de acuerdo con los estándares del proyecto BlackShot
RUN corepack enable && corepack prepare pnpm@latest --activate

# Copiar configuración de paquetes e instalar dependencias bloqueadas
COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile

# Copiar el código fuente del frontend y compilar
COPY . .
RUN pnpm run build

# ==========================================================
# Etapa 2: Servidor en Rust sobre Imagen SCRATCH (Vacía)
# ==========================================================
FROM joseluisq/static-web-server:2-scratch

# Copiar la compilación estática generada en SvelteKit al directorio público
COPY --from=build-frontend /app/build /public

# Copiar el archivo de configuración endurecido para SWS
COPY docker-sws-config.toml /config.toml

# Exponer el puerto del servidor estático
EXPOSE 8080

# Iniciar el servidor con configuración explícita
ENTRYPOINT ["/static-web-server", "--config-file", "/config.toml"]
```

#### [NUEVO] Configuración para el Servidor Web Rust (`docker/frontend/docker-sws-config.toml`)

```toml
[general]
host = "0.0.0.0"
port = 8080
root = "/public"
page-404 = "/public/404.html"
compression = true
security-headers = true # Activa automáticamente cabeceras como X-Frame-Options, X-Content-Type-Options, etc.

# Cabeceras personalizadas de seguridad avanzada
[advanced]
headers = [
    { name = "Content-Security-Policy", value = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; connect-src 'self' ws: wss: http: https:;" },
    { name = "X-Frame-Options", value = "DENY" },
    { name = "X-Content-Type-Options", value = "nosniff" },
    { name = "Referrer-Policy", value = "strict-origin-when-cross-origin" },
    { name = "Permissions-Policy", value = "geolocation=(), microphone=(), camera=()" }
]
```

---

### D. Nueva Configuración de Orquestación (`docker/docker-compose.yml`)

Este es el archivo `docker-compose.yml` completo y endurecido, integrando todos los runtime de solo lectura, políticas de no escalabilidad de privilegios, y remoción de puertos públicos para la base de datos.

```yaml
services:
  db:
    image: postgres:18-alpine
    container_name: blackshot_postgres
    restart: always
    environment:
      POSTGRES_USER: blackshot_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-blackshot_password}
      POSTGRES_DB: blackshot_db
    # Mantenemos el puerto oculto del exterior para evitar ataques automatizados.
    # Los otros contenedores se comunican internamente a través de la red del compose.
    expose:
      - "5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    
    # ENDURECIMIENTO DE RUNTIME POSTGRESQL:
    read_only: true                  # Bloqueo total de escritura en el sistema de archivos raíz
    tmpfs:
      - /run/postgresql:uid=70,gid=70 # Requerido para sockets de conexión interna (usuario postgres = 70)
      - /tmp:uid=70,gid=70           # Espacio temporal para operaciones del motor de BD
    cap_drop:
      - ALL                          # Remueve absolutamente todas las capacidades administrativas de Linux
    security_opt:
      - no-new-privileges:true       # Impide que procesos eleven privilegios en tiempo de ejecución
    
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U blackshot_user -d blackshot_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ..
      dockerfile: docker/backend/Dockerfile
    image: ${DOCKER_USER:-blackshot}/pos-backend:latest
    container_name: blackshot_backend
    restart: always
    env_file:
      - ../.env
    environment:
      - DATABASE_URL=postgresql+asyncpg://blackshot_user:${POSTGRES_PASSWORD:-blackshot_password}@db:5432/blackshot_db
    ports:
      # Exponemos el puerto de la API mapeado estrictamente a localhost (127.0.0.1)
      # Esto evita la exposición directa a Internet y canaliza el tráfico vía proxy local
      - "127.0.0.1:${BACKEND_PORT:-8000}:8000"
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - backend_data:/app/data
    
    # ENDURECIMIENTO DE RUNTIME BACKEND:
    read_only: true
    tmpfs:
      - /tmp:uid=10001,gid=10001     # Directorio temporal de lectura/escritura en RAM
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true

  sync_agent:
    build:
      context: ..
      dockerfile: docker/backend/Dockerfile
    image: ${DOCKER_USER:-blackshot}/pos-backend:latest
    container_name: blackshot_sync_agent
    restart: always
    env_file:
      - ../.env
    environment:
      - DATABASE_URL=postgresql+asyncpg://blackshot_user:${POSTGRES_PASSWORD:-blackshot_password}@db:5432/blackshot_db
    command: ["python", "-m", "bs_sync.agent"]
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - backend_data:/app/data
    
    # ENDURECIMIENTO DE RUNTIME SYNC AGENT:
    read_only: true
    tmpfs:
      - /tmp:uid=10001,gid=10001
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true

  frontend:
    build:
      context: ../bs_frontend
      dockerfile: ../docker/frontend/Dockerfile
    image: ${DOCKER_USER:-blackshot}/pos-frontend:latest
    container_name: blackshot_frontend
    restart: always
    ports:
      # El frontend escucha internamente en 8080 dentro de la imagen scratch
      - "${FRONTEND_PORT:-80}:8080"
    depends_on:
      - backend
    
    # ENDURECIMIENTO DE RUNTIME FRONTEND:
    read_only: true
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    user: 10001:10001                # Fuerza la ejecución bajo usuario no root en la imagen scratch

volumes:
  postgres_data:
  backend_data:
```

---

## 4. Endurecimiento del Host del Servidor (Capa del Kernel y Sistema Operativo)

Si los contenedores están completamente aislados, el vector restante es el acceso directo al servidor host de Linux. Presentamos las pautas para asegurar la máquina virtual/servidor VPS donde corre el ecosistema BlackShot.

### A. Desactivación o Enmascaramiento de SSH (Si es Infraestructura Inmutable)
Si implementas despliegues automatizados (donde las actualizaciones consisten en reconstruir y reemplazar la VM de forma inmutable), desactiva SSH por completo para mitigar intentos de intrusión y escaneo de puertos.

```bash
# Apagar, deshabilitar y enmascarar el demonio SSH
sudo systemctl stop sshd
sudo systemctl disable sshd
sudo systemctl mask sshd
```
*Para administrar la máquina en este esquema, utiliza la consola serial o la interfaz de terminal virtual nativa que proporciona tu proveedor de nube (AWS, GCP, DigitalOcean, Linode), protegida por Autenticación Multifactor (MFA).*

### B. Endurecimiento si SSH debe permanecer Activo
Si requieres mantener el acceso SSH para mantenimiento tradicional, edita `/etc/ssh/sshd_config` con una política ultra-restrictiva:

```ini
# /etc/ssh/sshd_config - Configuración Endurecida

# Cambiar el puerto por defecto para detener escaneos automatizados masivos
Port 2222

# Desactivar obligatoriamente la autenticación por contraseña tradicional
PasswordAuthentication no
PubkeyAuthentication yes

# Limitar intentos y sesiones concurrentes
MaxAuthTries 3
MaxSessions 2

# Permitir el acceso ÚNICAMENTE al usuario de despliegue configurado
AllowUsers tu_usuario_de_despliegue

# Bloquear redireccionamientos que puedan canalizar tráfico malicioso (túneles de red)
X11Forwarding no
AllowTcpForwarding no
AllowAgentForwarding no
ClientAliveInterval 300
ClientAliveCountMax 2
```
*Reinicia el demonio después de aplicar los cambios:* `sudo systemctl restart ssh` (o `sshd`).

### C. Bloqueo y Configuración Cortafuegos del Kernel (UFW / Netfilter)
Establece una política de "Denegar todo por defecto" tanto para entrada como para salida. Solo se permiten servicios estrictamente necesarios a nivel de Kernel.

```bash
# 1. Resetear todas las reglas existentes a denegación total
sudo ufw default deny incoming
sudo ufw default deny outgoing

# 2. Permitir resolución de DNS y sincronización de hora (NTP) de salida
# Requerido por el host y los contenedores para resolver dominios de sincronización
sudo ufw allow out 53/udp
sudo ufw allow out 123/udp

# 3. Permitir tráfico web HTTP y HTTPS de salida para descargar paquetes/actualizaciones (si es necesario)
sudo ufw allow out 80/tcp
sudo ufw allow out 443/tcp

# 4. Permitir tráfico de entrada de producción strictly necesario
sudo ufw allow 80/tcp  # HTTP (Frontend)
sudo ufw allow 443/tcp # HTTPS (Frontend con TLS)

# 5. Permitir SSH (Puerto alternativo) restringido únicamente desde tu IP estática o VPN privada
# Reemplaza X.X.X.X con tu IP de administración
sudo ufw allow from X.X.X.X to any port 2222 proto tcp

# 6. Activar el Firewall
sudo ufw enable
```

---

## 5. Plan de Verificación y Mitigación de Riesgos

La implementación de este plan de endurecimiento drástico requiere validar que la operatividad del ecosistema POS local y la sincronización con el Core Central no se rompan debido a los bloqueos de escritura y red.

### Pruebas de Funcionamiento Críticas:
1. **Verificación de Persistencia del Volumen de Postgres:**
   * Validar que los datos locales del POS no se pierdan al destruir y levantar la base de datos con las nuevas políticas. El volumen `postgres_data` persistido en `/var/lib/postgresql/data` no se verá afectado por el atributo `read_only: true` del sistema raíz.
2. **Creación de Sockets en `tmpfs`:**
   * Comprobar mediante los logs de docker (`docker logs blackshot_postgres`) que PostgreSQL arranca de forma exitosa y es capaz de crear el socket local `/run/postgresql/.s.PGSQL.5432` dentro del sistema temporal en memoria RAM.
3. **Escritura del Agente de Sincronización:**
   * Garantizar que la carpeta `/app/data` de `sync_agent` sea una montura de volumen válida y que cualquier escritura de archivos locales/estados de sincronización no sea bloqueada por la restricción de solo lectura del contenedor principal.
4. **Verificación de Red del Backend:**
   * Probar que FastAPI es inaccesible desde IPs externas al host en el puerto `8000`, pero que responde perfectamente a peticiones locales originadas en la misma máquina o desde un Proxy Reverso Nginx/Caddy del host.

---

## 6. Conclusión y Siguientes Pasos

Este plan provee un blindaje integral del sistema frente a ataques modernos en entornos de ejecución donde el host y su Kernel no son de total confianza. Al eliminar shells, privilegios de root, compiladores y puertos de bases de datos expuestos, la dificultad para lograr una intrusión o una escalada exitosa se incrementa exponencialmente.

**¿Cómo proceder?**
* **Aprobación del Plan:** Este borrador sirve como diseño técnico definitivo. Una vez revisado y aprobado por el usuario, se puede proceder a la creación física de los Dockerfiles endurecidos, la configuración del servidor web y la actualización del archivo `docker-compose.yml`.
