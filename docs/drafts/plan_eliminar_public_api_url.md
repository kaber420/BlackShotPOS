# Plan de Implementación: Eliminación de `PUBLIC_API_URL` y Consolidación de Rutas Relativas

Este plan describe los pasos técnicos para eliminar por completo la variable obsoleta y confusa `PUBLIC_API_URL` en todo el repositorio (tanto en el POS principal como en el Portal de Clientes), consolidando un sistema autoadministrado basado en rutas relativas y resolución dinámica.

---

## 🏗️ Cambios Propuestos

### 1. Eliminación de Variables y Plantillas de Entorno

#### [MODIFY] [.env.example](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/.env.example)
- Eliminar la línea `PUBLIC_API_URL=""` por completo de la plantilla ejemplar.

#### [MODIFY] [.env](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/.env), [bs_frontend/.env](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/bs_frontend/.env) y [bs_customer_portal/.env](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/bs_customer_portal/.env)
- Remover la línea `PUBLIC_API_URL="..."` de todos los archivos `.env` locales.

---

### 2. Refactorización en el Frontend del POS (`bs_frontend`)

#### [MODIFY] [api.ts](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/bs_frontend/src/lib/api.ts)
- Eliminar la importación de `PUBLIC_API_URL`.
- Modificar `fetchApi` para que use el path relativo directamente:
  ```typescript
  export async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
      const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
      // El navegador realiza la petición a su propio origen (localhost:5173/api/...)
      const url = path; 
  ```

#### [MODIFY] [pos_socket.svelte.ts](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/bs_frontend/src/lib/pos_socket.svelte.ts)
- Eliminar la importación de `PUBLIC_API_URL`.
- Cambiar la resolución del WebSocket para que sea 100% dinámica basándose en la barra de direcciones del navegador (`window.location`):
  ```typescript
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const host = window.location.host; // Detecta automáticamente IP local o dominio en caliente
  const url = `${protocol}://${host}/api/v1/pos/events/ws/pos`;
  ```

---

### 3. Refactorización en el Portal de Clientes (`bs_customer_portal`)

Eliminar la importación y uso de `PUBLIC_API_URL` y las constantes `apiBase`, simplificando los fetches a rutas relativas nativas.

#### [MODIFY] [login/+page.svelte](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/bs_customer_portal/src/routes/login/+page.svelte)
- Remover `PUBLIC_API_URL` y `apiBase`.
- Cambiar fetch a: `/api/v1/public/customers/auth/login`.

#### [MODIFY] [menu/+page.svelte](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/bs_customer_portal/src/routes/menu/+page.svelte)
- Remover `PUBLIC_API_URL` y `apiBase`.
- Cambiar fetches a rutas relativas `/api/...`.

#### [MODIFY] [perfil/+page.svelte](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/bs_customer_portal/src/routes/perfil/+page.svelte)
- Remover `PUBLIC_API_URL` y `apiBase`.
- Cambiar fetches a rutas relativas `/api/...`.

#### [MODIFY] [ProductMedia.svelte](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/bs_customer_portal/src/lib/components/ProductMedia.svelte)
- Remover `PUBLIC_API_URL` y `apiBase`.
- Cambiar resolución de imágenes relativas para que apunten al mismo origen:
  ```typescript
  let fullUrl = $derived(src && !src.startsWith('http') ? src : src);
  ```

---

### 4. Refactorización del Backend (`pos_core`)

#### [MODIFY] [setup.py](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/pos_core/setup.py)
- Remover `"PUBLIC_API_URL"` de la lista `keys_to_ensure` en `_ensure_secure_tokens` para evitar que el script de inicio intente regenerarla u obligue a escribirla de nuevo.
- **[NUEVA MEJORA DE DX]** Implementar `input_with_timeout` para evitar bloqueos del CLI:
  - Crear una función robusta para leer `stdin` usando el módulo `select` de Python con soporte para entornos no interactivos (`isatty`).
  - Si el usuario no responde en **5 segundos**, o si el entorno no es interactivo (como en Docker o daemons de fondo), el script seleccionará automáticamente la opción **`[s]`** (Autorizar IP local y activar Binding Estricto).
  - Al seleccionar `s`, también guardará `SKIP_IP_PROMPT="true"`, por lo que los futuros arranques serán completamente instantáneos e invisibles.

---

## 📡 Plan de Verificación

### Pruebas Manuales
1. Reiniciar los servidores de desarrollo tanto de `bs_frontend` como de `bs_customer_portal`.
2. Verificar que el flujo de login del POS sigue funcionando al 100%.
3. Verificar que el flujo del socket del POS conecta exitosamente.
4. Verificar que el Portal de Clientes carga el catálogo y permite loguearse y ver perfil usando únicamente rutas relativas nativas sin variables externas.
5. **Verificar el Timeout del CLI:** Arrancar `blackshot run` en una red con IP no configurada y comprobar que a los 5 segundos avanza de forma autónoma seleccionando `[s]` sin colgar la terminal.

