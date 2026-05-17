# Documento Técnico: Conexión Segura con la Central Remota (NKEY y TLS)

Este documento detalla la arquitectura, configuración y manual de uso de la comunicación cifrada y segura entre las sucursales locales del **Blackshot POS** y el **Central Core** remoto, implementada mediante curvas elípticas Ed25519 (NKEY), cifrado obligatorio en tránsito (TLS/SSL), diagnósticos de red interactivos (CLI) y un servicio de estado compartido.

---

## 1. Arquitectura de Seguridad y Flujo de Comunicación

Para garantizar la integridad, privacidad y autenticación fuerte de la transmisión de datos (ventas, inventario y pings de presencia), la comunicación se basa en tres pilares:

### Pilar A: Autenticación Criptográfica con NKEY (Ed25519)
En lugar de contraseñas o tokens simétricos compartidos, se utiliza el estándar **NKEY** de NATS (basado en firmas criptográficas de curvas elípticas Ed25519):
1. **Generación de Claves**: El POS genera de forma local y atómica un par de llaves: la semilla privada (`NATS_NKEY_SEED`) y el identificador público (`NATS_NKEY_PUBLIC`).
2. **Resguardo del Seed**: La semilla privada permanece exclusivamente en la máquina del POS local en el archivo `.env` y nunca viaja por la red.
3. **Registro en Central**: El `Public ID` se registra en el Central Core.
4. **Desafío Criptográfico**: Al conectar, el servidor NATS envía un desafío aleatorio (nonce). El agente de sincronización (`bs_sync.agent`) firma este nonce usando la clave privada local y la envía de vuelta. El servidor valida la firma usando el Public ID previamente autorizado.

### Pilar B: Cifrado en Tránsito (TLS/SSL)
Toda la información viaja obligatoriamente cifrada de extremo a extremo a través de internet público para evitar ataques de intermediarios (Man-in-the-Middle):
- Si la URL de conexión configurada en base de datos (`nats_url`) inicia con los esquemas seguros `tls://` o `ssl://`, el cliente NATS inicializa un contexto seguro `ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)` para negociar de forma estricta el handshake TLS.

### Pilar C: Estado y Monitoreo Compartido
Dado que el **FastAPI API Server** y el **Sync Agent** se ejecutan como procesos independientes en el POS (desacoplados para robustez ante caídas), se utiliza un archivo de estado compartido muy ligero en `data/sync_status.json`:
- El agente de sincronización actualiza este archivo en tiempo real al conectarse, desconectarse, reportar errores o registrar pings exitosos.
- El servidor FastAPI expone esta información instantáneamente al frontend mediante el endpoint público `/api/sync/status`.

---

## 2. Variables de Entorno (.env)

El sistema de seguridad NKEY añade dos nuevas variables clave en el archivo `.env` local de la sucursal:

```env
# Semilla criptográfica privada (SU...) - ¡MANTENER SECRETA!
NATS_NKEY_SEED="SUANQJB4HLAQMFA2ETN62..."

# Identificador público de la sucursal (U...)
NATS_NKEY_PUBLIC="UC23Q5UNPB3JFLPJ7HIJ..."
```

---

## 3. Manual de Operación y Comandos del CLI (`blackshot`)

Se han integrado comandos nativos interactivos para autogestionar la criptografía y realizar pruebas preventivas de red:

### A. Inicializar y Generar Credenciales
Para crear el par de llaves Ed25519 de forma atómica y segura en el archivo `.env`:
```bash
blackshot security generate-keys
```
*Nota: Si ya existen llaves configuradas en el `.env`, el comando detectará la presencia de credenciales y pedirá confirmación explícita al usuario para evitar sobrescribir accidentalmente la identidad de la sucursal.*

### B. Mostrar el Public ID de la Sucursal
Para consultar y copiar fácilmente el ID que debe registrarse en la Central Remota:
```bash
blackshot security show-id
```
**Ejemplo de salida:**
```text
============================================================
🔑 PUBLIC ID DE LA SUCURSAL (NKEY)
============================================================
 UC23Q5UNPB3JFLPJ7HIJ2FSBJBRAPQMGF7VEY6RSZAEMGERBSVLFA7OF
============================================================
Copia este ID y regístralo en la Central Remota para autorizar
la sincronización segura de esta sucursal.
============================================================
```

### C. Suite de Autodiagnóstico de Red (`blackshot sync test`)
Permite al operador o desarrollador probar de forma preventiva y secuencial el estado de la conexión a la Central sin necesidad de iniciar todos los servicios del POS.

```bash
blackshot sync test
```

**Ejemplo de flujo del reporte:**
```text
============================================================
📡 INICIANDO AUTODIAGNÓSTICO DE CONEXIÓN CON LA CENTRAL REMOTA
============================================================
⚙️  Paso 1: Cargando configuración de NATS...
   [OK] Configuración cargada: Branch=branch_default, NATS=nats://localhost:4222

🔍 Paso 2: Resolviendo DNS para localhost...
   [OK] Resuelto exitosamente a IP: 127.0.0.1 (Tiempo: 0.06ms)

🔌 Paso 3: Probando conectividad TCP a localhost:4222...
   [OK] Puerto de red abierto. Conexión de socket exitosa (Tiempo: 0.12ms)

🔐 Paso 4: Validando llaves criptográficas NKEY locales...
   [OK] Criptografía Ed25519 validada con éxito.
   [OK] Seed local correcta. Public ID: UC23Q5UNPB3JFLPJ7HIJ2FSBJBRAPQMGF7VEY6RSZAEMGERBSVLFA7OF

🤝 Paso 5: Realizando handshake NATS completo...
   [OK] Conexión establecida y autenticada con éxito!
   [OK] Handshake TLS y autenticación completados.
   📈 Latencia de conexión (RTT): 2.45ms

============================================================
🎉 AUTODIAGNÓSTICO EXITOSO: ¡La sucursal está lista para operar de forma segura!
============================================================
```

---

## 4. API Local de Estado (`/api/sync/status`)

La interfaz del POS (frontend) puede consultar en todo momento el estado en tiempo real de la conexión remota realizando una petición `GET` al endpoint local:

`GET http://localhost:8000/api/sync/status`

### Estructuras de Respuesta JSON:

#### Estado En Línea (Online):
```json
{
  "status": "online",
  "last_ping_at": "2026-05-17T14:56:04.123456",
  "error": null
}
```

#### Estado Fuera de Línea (Offline con error de red):
```json
{
  "status": "offline",
  "last_ping_at": "2026-05-17T14:56:04.123456",
  "error": "[Errno 111] Connection refused"
}
```

#### Agente no iniciado:
```json
{
  "status": "offline",
  "last_ping_at": null,
  "error": "Agente de sincronización no iniciado"
}
```
