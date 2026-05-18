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
