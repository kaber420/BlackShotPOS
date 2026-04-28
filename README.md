# Blackshot Ecosystem ☕ & ☁️

> **Blackshot** es una plataforma integral para cafeterías que combina un potente **Punto de Venta (POS)** local con una **Central de Gestión** para el monitoreo y administración multi-sucursal en tiempo real.

---

## 🏗️ Arquitectura del Ecosistema

El proyecto se divide en tres componentes principales:

1.  **Blackshot POS (Local):** La interfaz de ventas, gestión de inventario local, mesas y cocina. Funciona en cada sucursal.
2.  **Blackshot Central:** El cerebro administrativo. Permite gestionar múltiples regiones, sucursales, catálogos globales y ver analíticas consolidadas.
3.  **Blackshot Sync Agent:** El puente. Un agente ligero que sincroniza automáticamente las ventas y el estado local de cada POS con la Central.

---

## 🚀 Instalación y Configuración

### Requisitos previos

- Python **3.9+**
- Node.js **18+**
- `pip` y `venv` disponibles

### 1. Clonar el repositorio

```bash
git clone https://github.com/kaber420/blackshot.git
cd blackshot
```

---

### 📦 Componente: Blackshot POS (Sucursal)

#### Configuración del Backend POS
```bash
# Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -e .

# Inicializar base de datos y datos de prueba
python scripts/seed_data.py

# Iniciar servidor POS
blackshot
```

#### Configuración del Frontend
```bash
cd bs_frontend
npm install
npm run dev
```
> Acceso: `http://localhost:5173` | API: `http://localhost:8000`

---

### ☁️ Componente: Blackshot Central

La gestión central se realiza de forma independiente dentro de su propio directorio.

```bash
cd saas_core

# Crear y activar entorno virtual específico (opcional pero recomendado)
python -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -e .

# Poblar con datos iniciales (Regiones, Sucursales, Usuarios Globales)
python seed_central.py

# Iniciar Central
blackshot-central
```
> El Dashboard administrativo estará disponible por defecto en `http://localhost:8001`.

---

### 🔄 Sincronización POS -> Central

Para activar la sincronización, el agente de cada sucursal debe estar corriendo:

```bash
# Con el entorno virtual principal activo
python -m bs_sync.agent
```

---

## 📁 Estructura del Proyecto

```
blackshot/
├── pos_core/       # Lógica del POS local (Ventas, Inventario, Mesas)
├── saas_core/      # Dashboard central, gestión multi-sucursal y regiones
├── bs_sync/        # Agente de sincronización de datos
├── bs_frontend/    # Interfaz web moderna (SvelteKit)
├── scripts/        # Utilidades de mantenimiento y seeding
├── docs/           # Documentación estratégica y manuales
├── drafts/         # Planes de desarrollo futuro
└── pyproject.toml  # Configuración base del proyecto
```

---

##  Licencia y Atribución Obligatoria ⚖️

Este proyecto se protege bajo la **GNU AGPL-3.0**. Queremos que Blackshot sea el motor de tu cafetería o Gestión Centralizada, pero el uso del código conlleva responsabilidades legales:

###  Opción A: Colaborar (Recomendado)
Si realizas aportes al proyecto (Pull Requests, solución de bugs, mejoras documentadas), te otorgamos una **excepción de buena fe**. Esto te permite:
-  **No publicar** el resto de tu código privado/comercial.
-  **Omitir la mención** o enlace al autor en tu interfaz.
- *Nosotros ganamos una mejora, tú ganas privacidad.*

###  Opción B: Uso sin Aportes (Atribución Obligatoria)
Si decides usar Blackshot sin colaborar de ninguna forma, la AGPL-3.0 exige **estricto cumplimiento**:
1.  **Código Abierto:** Cualquier modificación que hagas debe ser publicada bajo AGPL-3.0.
2.  **Atribución visible:** Debes incluir un enlace directo a este repositorio y una mención clara al autor (**Blackshot POS / @kaber420**) en una sección "Acerca de" o en el pie de página de tu aplicación.
3.  **No remover avisos:** No puedes eliminar los avisos de copyright del código fuente.

---

##  Contribuir

1. Haz un fork del repositorio
2. Crea tu rama: `git checkout -b feature/mi-mejora`
3. Haz commit de tus cambios: `git commit -m 'feat: descripción de mejora'`
4. Abre un Pull Request
