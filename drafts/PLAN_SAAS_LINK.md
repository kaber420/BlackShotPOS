# Plan: SaaS Branch Link & Identity Management

Este plan detalla cómo implementar un flujo de trabajo para vincular sucursales locales (POS) con la Central SaaS, asegurando que cada evento sincronizado esté correctamente identificado y que la comunicación sea segura.

## 1. El Problema
Actualmente, las sucursales locales utilizan un identificador genérico (`branch_default`). Cuando envían datos al SaaS, el servidor central no puede asociar esos datos con una sucursal registrada en su base de datos, resultando en logs de "Sucursal Desconocida".

## 2. Objetivos
- Facilitar la vinculación de un POS con el SaaS mediante un proceso de "Emparejamiento".
- Asegurar que el SaaS reconozca el nombre y configuración de cada sucursal al recibir eventos.
- Proporcionar una interfaz clara para que el administrador gestione los IDs y llaves de conexión.

## 3. Propuesta Técnica

### Fase A: Central SaaS (Panel Administrativo)
1.  **Generación de Configuración**: Al crear una sucursal en el panel central, se deben mostrar claramente los datos necesarios para la conexión:
    - **Branch ID**: El UUID generado por el SaaS.
    - **NATS URL**: La dirección del servidor de eventos.
    - **Bridge Public Key**: La llave pública para validar el acceso remoto.
2.  **Modal de Conexión**: Añadir un botón "Conectar POS" en `sucursales.html` que abra un modal con estos datos listos para copiar.

### Fase B: POS Local (Administración)
1.  **UI de Sincronización**: En la página de configuración (`admin/config`), añadir una pestaña o sección dedicada a "SaaS & Sincronización".
2.  **Campos de Configuración**: Permitir al usuario ingresar:
    - `branch_id`: El ID entregado por el SaaS.
    - `nats_url`: Dirección del servidor NATS.
    - `bridge_enabled`: Toggle para activar el Bridge.
    - `bridge_public_key`: Área de texto para la llave RSA.
3.  **Persistencia**: Asegurar que estos cambios se guarden en la tabla `BusinessSettings` de la base de datos local.

### Fase C: Agente de Sincronización
1.  **Uso de Identidad Real**: El agente (`bs_sync/agent.py`) ya lee el `branch_id` de la base de datos. Al actualizar la configuración en la Fase B, el agente comenzará a publicar automáticamente con el nuevo ID en el siguiente ciclo.
2.  **Validación de Conexión**: Implementar un botón de "Probar Conexión" en el POS que verifique si puede alcanzar el servidor NATS.

## 4. Flujo de Trabajo del Usuario
1.  El admin entra al **SaaS** y crea la sucursal "Sucursal Condesa".
2.  Copia el **Branch ID** (ej: `550e8400-e29b-41d4-a716-446655440000`).
3.  Entra al **POS Local** -> Configuración -> SaaS.
4.  Pega el ID y activa la sincronización.
5.  El POS comienza a enviar eventos como `branches.550e8400-e29b-41d4-a716-446655440000.sales.payment_added`.
6.  El SaaS recibe el evento, busca el ID en su base de datos, encuentra "Sucursal Condesa" y registra la venta correctamente.

## 5. Próximos Pasos Sugeridos
- [ ] Implementar el Modal de Conexión en el SaaS.
- [ ] Actualizar el formulario de configuración en el POS Frontend.
- [ ] Crear un script de "Ping" para que el POS notifique al SaaS que está online periódicamente.
