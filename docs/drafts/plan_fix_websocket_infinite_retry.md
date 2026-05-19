# Plan de Implementación: Solución de Bucle Infinito en WebSocket del POS

Este plan describe las acciones técnicas necesarias para corregir un fallo crítico de fuga de conexiones en segundo plano, donde el cliente WebSocket (`posSocket`) del frontend sigue reintentando conectarse infinitamente cada 3 segundos en la pantalla de login (usuario no autenticado), saturando los logs y las conexiones rechazadas del servidor con errores 401.

---

## 🏗️ Análisis del Problema

1. **Condición de Carrera en Carga Inicial:**
   - Al cargar el POS sin estar autenticado, `(app)/+layout.svelte` ejecuta `initAuth()`.
   - `initAuth()` captura el error 401 del backend, establece `appState.isLoggedIn = false`, y en su bloque `finally` pone `appState.permissionsLoaded = true`.
   - Debido a que `permissionsLoaded` es `true`, el layout monta reactivamente `(app)/+page.svelte` (la página protegida) por una fracción de segundo antes de ser redirigido.
   - Al montarse la página principal, su `onMount` se ejecuta y llama a `posSocket.subscribe("dashboard_stats")`, lo que inicializa e intenta conectar el WebSocket.
   - En paralelo, el `onMount` del layout falla en `checkActiveShift()`, captura el error y ejecuta `goto('/login')` de forma cliente (sin recargar la ventana).
   
2. **Fuga en Memoria del Socket:**
   - La redirección a `/login` es una transición interna de SvelteKit que no recarga la página física.
   - El socket iniciado vive en un Singleton de JS en memoria, por lo que sigue intentando conectarse.
   - Al no tener cookies/tokens válidos, el servidor de FastAPI rechaza la conexión con `code=1008` (Unauthorized) continuamente.
   - La lógica del socket interpreta el cierre como una caída de red y vuelve a intentar conectarse cada 3 segundos de manera indefinida.

---

## 🏗️ Cambios Propuestos

### 1. Robustecer la lógica de inicialización en el Frontend

#### [MODIFY] [app_state.svelte.ts](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/bs_frontend/src/lib/app_state.svelte.ts)
- Cambiar la lógica en `initAuth()` para que si ocurre un fallo en la llamada de autenticación a `/api/users/me`, no se marquen los permisos como cargados (`permissionsLoaded = false`), evitando que el layout renderice el contenido protegido antes del redirect.
- Asegurar que `permissionsLoaded` solo se vuelva `true` si el login es completamente válido.

```typescript
export async function initAuth(): Promise<boolean> {
    appState.permissionsLoaded = false;
    try {
        const data = await fetchApi<any>('/api/users/me');

        appState.isLoggedIn  = true;
        appState.userUuid    = data.id;
        appState.userName    = data.username;
        
        const metadata = data.custom_metadata || {};
        appState.userRole    = metadata.role || 'waiter';
        
        const rolePreset = ROLE_PRESETS_JS[appState.userRole] || ROLE_PRESETS_JS['waiter'];
        appState.permissions = { ...rolePreset, ...(metadata.permissions || {}) };
        
        try {
            appState.settings = await SettingsService.get();
        } catch (e) {
            console.warn("Usando configuración por defecto (error en SettingsService)");
        }

        appState.permissionsLoaded = true; // Solo si se cargó exitosamente
        return true;
    } catch (error) {
        appState.isLoggedIn = false;
        appState.permissionsLoaded = false; // Mantener bloqueado el layout si no hay sesión
        return false;
    }
}
```

---

### 2. Implementar Guardia de Autenticación en el Gestor de Sockets

#### [MODIFY] [pos_socket.svelte.ts](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/bs_frontend/src/lib/pos_socket.svelte.ts)
- Modificar el método `connect()` para que compruebe `appState.isLoggedIn`. Si es `false`, se sale inmediatamente sin conectar.
- Modificar el método `subscribe()` para que no intente conectar si no hay sesión activa.

```typescript
    connect() {
        if (typeof window === 'undefined') return;
        
        // Evitar conexión si no hay sesión activa
        if (!appState.isLoggedIn) {
            console.log("🔌 SOCKET: Intento de conexión abortado (Usuario no autenticado)");
            this.status = 'closed';
            return;
        }
        
        this.isManuallyClosed = false;
        ...
```

Y en `subscribe()`:
```typescript
    subscribe(topic: string) {
        this.subscribedTopics.add(topic);
        if (this.status === 'open' && this.socket) {
            this.socket.send(JSON.stringify({ action: "subscribe", topic }));
        } else if (this.status === 'closed' && appState.isLoggedIn) {
            this.connect();
        }
    }
```

---

### 3. Limpieza de Sockets en Logout

#### [MODIFY] [app_state.svelte.ts](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/bs_frontend/src/lib/app_state.svelte.ts)
- Importar y usar `posSocket.close()` en `logout()` para garantizar que la conexión se detenga de forma proactiva al salir de la aplicación.

```typescript
import { posSocket } from './pos_socket.svelte';

export async function logout() {
    try {
        posSocket.close(); // Cerrar el socket limpiamente
        await fetchApi('/api/auth/jwt/logout', { method: 'POST' });
    } catch (e) {
        console.error("Error al cerrar sesión en el servidor:", e);
    } finally {
        setAuth(false);
        if (typeof window !== 'undefined') {
            window.location.href = '/login';
        }
    }
}
```

---

## 📡 Plan de Verificación

### Pruebas Manuales
1. **Verificación de Login Limpio (Sin Sockets en segundo plano):**
   - Cargar la raíz `/` en modo incógnito (no logueado).
   - Comprobar en la consola del navegador que el usuario es redirigido a `/login` sin mostrar peticiones de WebSocket fallidas en bucle de 3 segundos en la pestaña de Red.
2. **Verificación de Conexión en Caliente:**
   - Loguearse con credenciales válidas.
   - Comprobar que el socket conecta exitosamente (`🔌 SOCKET: Conectado`) y recibe actualizaciones.
3. **Verificación tras Deslogueo:**
   - Hacer clic en "Cerrar Sesión".
   - Comprobar que el socket se cierra de inmediato y no quedan intentos pendientes en la pestaña `/login`.
4. **Verificación de Logs del Servidor:**
   - Asegurarse de que el backend de FastAPI no reciba advertencias de `Intento de conexión no autorizada` de forma repetitiva cuando no hay usuarios activos.
