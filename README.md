# Blackshot POS ☕

> Sistema de Punto de Venta (POS) diseñado para cafeterías. Gestiona pedidos, inventario, roles de usuario, cocina (KDS) y reportes desde una sola interfaz moderna.

---

##  Instalación

### Requisitos previos

- Python **3.9+**
- Node.js **18+**
- `pip` y `venv` disponibles en el sistema

---

### 1. Clonar el repositorio

```bash
git clone https://github.com/kaber420/blackshot.git
cd blackshot
```

---

### 2. Configurar el entorno virtual e instalar el backend

```bash
# Crear el entorno virtual
python -m venv .venv

# Activar el entorno virtual
# En Linux / macOS:
source .venv/bin/activate

# En Windows (PowerShell):
# .venv\Scripts\Activate.ps1
```

Instalar el paquete y todas sus dependencias desde `pyproject.toml`:

```bash
pip install -e .
```

> El flag `-e` instala el paquete en modo editable, ideal para desarrollo. Para una instalación normal omite ese flag.

Para instalar también las dependencias de testing:

```bash
pip install -e ".[test]"
```

---

### 3. Configurar variables de entorno

Copia el archivo de ejemplo y edita los valores según tu entorno:

```bash
cp .env.example .env
```

---

### 4. Inicializar la base de datos

```bash
# (Opcional) Ejecutar migraciones si es necesario
python scripts/migrate_add_recipe.py

# Poblar con datos de prueba
python scripts/seed_data.py
```

---

### 5. Iniciar el servidor backend

Con el entorno virtual activo, usa el comando CLI instalado:

```bash
blackshot
```

Esto levanta el servidor **FastAPI** con Uvicorn. Por defecto estará disponible en `http://localhost:8000`.

---

### 6. Iniciar el frontend

En una terminal separada:

```bash
cd bs_frontend
npm install
npm run dev
```

El frontend estará disponible en `http://localhost:5173` (o el puerto que indique SvelteKit).

---

##  Testing

Asegúrate de tener el entorno virtual activo y las dependencias de test instaladas:

```bash
pytest
```

---

##  Estructura del Proyecto

```
blackshot/
├── pos_core/       # Lógica de negocio: inventario, ventas, órdenes, roles
├── omni_auth/      # Módulo de autenticación y gestión de usuarios
├── bs_frontend/    # Aplicación frontend en SvelteKit
├── scripts/        # Utilidades de migración y seeding
├── docs/           # Documentación estratégica
├── drafts/         # Planes de implementación de nuevas características
└── pyproject.toml  # Configuración del proyecto y dependencias
```

---

##  Licencia y Atribución Obligatoria ⚖️

Este proyecto se protege bajo la **GNU AGPL-3.0**. Queremos que Blackshot sea el motor de tu cafetería o SaaS, pero el uso del código conlleva responsabilidades legales:

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

### ⚖️ Nota Legal sobre Colaboraciones
Para facilitar este modelo de "Aporte x Privacidad", al enviar una contribución (Pull Request) a este repositorio, el colaborador acepta que su código se distribuya bajo AGPL-3.0 pero otorga a los mantenedores de Blackshot POS el derecho de administrar la licencia y conceder las excepciones descritas en la **Opción A** a otros usuarios. Esto asegura que podamos seguir ofreciendo flexibilidad a quienes ayudan a crecer el proyecto.

> **Resumen:** Si el código te es útil y no quieres compartir tus cambios ni dar crédito, la única forma de estar legalmente exento es haciendo un aporte al repositorio oficial. De lo contrario, la mención y el enlace son **obligatorios**.

---

**Cualquier duda o propuesta de colaboración especial, abre un Issue o contacta con los mantenedores. ¡Hagamos crecer Blackshot juntos!** 

---

##  Contribuir

1. Haz un fork del repositorio
2. Crea tu rama: `git checkout -b feature/mi-mejora`
3. Haz commit de tus cambios: `git commit -m 'feat: descripción de mejora'`
4. Abre un Pull Request

Consulta [`docs/`](./docs) para lineamientos de arquitectura y roadmap del proyecto.
