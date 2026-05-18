# Guía de Despliegue en SBC con Armbian (ARM64)

Esta guía detalla el paso a paso para compilar, configurar y desplegar los contenedores endurecidos de **BlackShotPOS** en una computadora de placa única (SBC) que ejecute **Armbian (ARM64)**, optimizando el sistema para proteger la vida útil de la tarjeta MicroSD.

---

## 1. Preparación del Sistema en la SBC Armbian

Antes de comenzar, asegúrate de que tu sistema Armbian tenga instaladas las herramientas esenciales.

### A. Instalar Docker y Docker Compose
En Armbian, puedes instalar Docker de forma rápida y limpia usando el comando oficial de conveniencia o a través de `armbian-config`:

```bash
# Actualizar repositorios del sistema
sudo apt update && sudo apt upgrade -y

# Instalar Docker usando el script oficial
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Añadir tu usuario al grupo docker para no usar 'sudo' en cada comando
sudo usermod -aG docker $USER

# Instalar Docker Compose (V2)
sudo apt install docker-compose-plugin -y
```
*(Nota: Reinicia tu sesión SSH o la SBC para que se aplique el grupo `docker` sin sudo).*

### B. Instalar pnpm (Opcional - Solo para Estrategia A)
Si decides compilar los archivos directamente sobre los recursos de tu SBC:
```bash
# Instalar Node.js y npm si no están
sudo apt install nodejs npm -y

# Instalar pnpm de forma global
sudo npm install -g pnpm
```

> [!TIP]
> Si utilizas la **Estrategia B (Compilación Cruzada en PC)**, **NO** es necesario instalar Node.js ni pnpm en tu SBC. Esto mantiene el sistema operativo de tu placa sumamente ligero y libre de dependencias pesadas que acortan la vida útil del almacenamiento.

---

## 2. Estrategia de Despliegue A: Compilación Directa en Armbian (Nativa)

Esta es la forma directa si deseas manejar todo dentro de la SBC sin usar una PC secundaria.

### Paso 1: Clonar y configurar entorno en la SBC
```bash
# Clonar tu repositorio en la placa
git clone <tu-repositorio-blackshot>
cd BlackShotPOS

# Crear y configurar el archivo de variables de entorno
cp .env.example .env
nano .env # Define tus contraseñas seguras aquí
```

### Paso 2: Compilar el proyecto en la SBC
Ejecuta el script de construcción sin parámetros. Al estar corriendo físicamente sobre la CPU ARM64 de Armbian, compilará todo de forma nativa para esa arquitectura:
```bash
bash scripts/docker-build.sh
```

### Paso 3: Encender los contenedores
```bash
docker compose -f docker/docker-compose.yml up -d
```

---

## 3. Estrategia de Despliegue B: Compilación Cruzada en PC AMD64 (Altamente Recomendado)

Esta estrategia es la mejor opción porque **no calienta la SBC** ni consume su memoria RAM/CPU en tareas pesadas de compilación. Generas las imágenes `linux/arm64` nativas directamente desde tu potente procesador `x86_64 / amd64`.

### Paso 1: Preparación del Entorno en la PC (Host AMD64)
Para compilar cruzado a ARM64, necesitas asegurar estas herramientas en tu PC de desarrollo:

1. **Docker Buildx:** El plugin de Docker para compilar en múltiples arquitecturas.
2. **QEMU Emulación binfmt:** Permite a tu CPU AMD64 ejecutar binarios ARM64 de forma transparente durante las fases del Dockerfile.
3. **pnpm local:** El script de construcción compilará los activos estáticos del frontend en tu PC antes de empaquetar el contenedor.

Ejecuta en la terminal de tu PC AMD64:
```bash
# 1. Instalar el plugin de Docker Buildx (si usas Linux/Ubuntu)
sudo apt update && sudo apt install docker-buildx -y

# 2. Registrar los emuladores multi-arquitectura en el kernel de Docker
docker run --privileged --rm tonistiigi/binfmt --install all

# 3. Verificar que buildx está disponible
docker buildx version
```

---

### Paso 2: Compilar cruzado para ARM64
Asegúrate de estar en la raíz de tu proyecto en la terminal de tu PC de desarrollo y lanza la compilación:
```bash
bash scripts/docker-build.sh --arm64
```
> [!NOTE]
> Este comando compilará el frontend localmente con tu `pnpm` y después utilizará Docker Buildx para generar las imágenes de backend y frontend compiladas en código máquina `ARM64`. Una vez terminadas, las cargará automáticamente (`--load`) en tu motor Docker local.

---

### Paso 3: Guardar y empaquetar las imágenes en tu PC
Exporta las imágenes de Docker a archivos comprimidos `.tar.gz` listos para ser guardados, respaldados o transferidos mediante tu método preferido (USB, red local, etc.):

```bash
# Guardar la imagen de backend y agente de sincronización para ARM64
docker save blackshot/pos-backend:latest | gzip > pos-backend-arm64.tar.gz

# Guardar la imagen del frontend (SvelteKit en Nginx) para ARM64
docker save blackshot/pos-frontend:latest | gzip > pos-frontend-arm64.tar.gz
```

---

### Paso 4: Cargar e iniciar las imágenes en Armbian
Una vez que hayas transferido los archivos `.tar.gz` y el directorio de configuraciones `docker/` con su archivo `.env` a la SBC, ejecuta en la placa:

```bash
# 1. Cargar las imágenes comprimidas en el motor Docker local de la SBC
docker load < pos-backend-arm64.tar.gz
docker load < pos-frontend-arm64.tar.gz

# 2. Navegar a la carpeta de configuraciones de tu proyecto en la SBC e iniciar
cd BlackShotPOS/
docker compose -f docker/docker-compose.yml up -d
```

---

## 4. Consejos de Oro para Proteger tu Tarjeta MicroSD en Armbian

Las tarjetas SD en las SBCs suelen dañarse debido a operaciones constantes de lectura/escritura en disco. Nuestra configuración de contenedores endurecidos ya protege tu hardware de la siguiente manera:

1. **Uso Intensivo de `tmpfs` (RAM):**
   * El estado de sincronización (`/app/data`), las carpetas temporales (`/tmp`) y el caché de Nginx corren 100% en la memoria RAM de tu SBC, reduciendo las escrituras en la tarjeta SD a **cero** durante las operaciones diarias del POS.
2. **Persistencia en Postgres:**
   * Solo la base de datos de transacciones de PostgreSQL (`postgres_data`) escribe en la tarjeta SD de forma controlada cuando realizas una venta.

### Recomendación extra en Armbian: Activar Armbian Ramlog
Armbian incluye por defecto una utilidad llamada **Ramlog** que almacena todos los logs del sistema operativo en RAM en lugar de la tarjeta SD. Asegúrate de que esté activa:
```bash
# Verificar estado de ramlog
systemctl status armbian-ramlog
```
Si no está activo, puedes configurarlo ejecutando `sudo armbian-config` en la terminal y dirigiéndote a la sección de configuración del sistema.

---

## 5. Verificación de Funcionamiento en la SBC

Una vez que los contenedores estén corriendo en Armbian, puedes auditar su correcto estado ejecutando:

```bash
# Ver estado de los contenedores
docker compose -f docker/docker-compose.yml ps

# Monitorear logs en tiempo real
docker compose -f docker/docker-compose.yml logs -f
```

La aplicación estará lista y accesible desde cualquier dispositivo de tu cafetería conectado a la misma red WiFi ingresando a la IP local de tu SBC (Puerto `80` por defecto).
