# Protocolo de API Unificado: TablePad IoT
**Versi\xc3\xb3n:** 2.0.0 (Diner-Focused)
**Estado:** Definici\xc3\xb3n de Arquitectura

Este documento define el lenguaje universal que hablan los terminales **Blackshot TablePad** (ESP32) para comunicarse con el ecosistema Blackshot.

---

## 1. Arquitectura de Comunicaci\xc3\xb3n
El sistema soporta dos v\xc3\xadas de integraci\xc3\xb3n, ambas convergen en el **Esquema JSON Nativo**:

### A. Integraci\xc3\xb3n Nativa (Directa)
Para el **Blackshot POS** original. El servidor se conecta directamente al terminal v\xc3\xada WebSocket. 
- **Ventaja:** Menor latencia, control total de seguridad y estados de hardware.
- **Protocolo:** [SPEC_NATIVE_JSON.md](file:///home/kaber420/Documentos/proyectos/blackshot_iot/SPEC_NATIVE_JSON.md)

### B. Integraci\xc3\xb3n v\xc3\xada Bridge (Adaptador)
Para conectar POS de terceros (Clover, Toast, Square, etc.) que no hablan el idioma del TablePad.
- **Funcionamiento:** Un middleware (Bridge) recibe el webhook del POS externo y lo **traduce** al Esquema JSON Nativo antes de enviarlo al terminal.
- **Prop\xc3\xb3sito:** Permitir que cualquier restaurante use el hardware TablePad sin cambiar su sistema de ventas actual.

---

## 2. Flujo de Datos Maestro (POS \xe2\x86\x92 Dispositivo)

### Gesti\xc3\xb3n de \xc3\x93rdenes (`order_new` / `order_update`)
Cualquier actualizaci\xc3\xb3n en el POS (un plato nuevo, cambio a 'Listo') debe enviarse con la estructura de **Evento + Datos**.

```json
{
  "event": "order_update",
  "data": {
    "order_id": 1234,
    "table_id": 5,
    "status": "LISTO",
    "progress": 100
  }
}
```

### Personalizaci\xc3\xb3n Din\xc3\xa1mica (`rebrand`)
El POS puede enviar en cualquier momento un cambio de identidad para que el terminal se ajuste al restaurante o a la mesa espec\xc3\xadfica.

---

## 3. Acciones de Mesa (Dispositivo \xe2\x86\x92 POS)
Cuando el comensal interact\xc3\xbaa con el **TablePad**, este notifica al POS mediante **Acciones**.

*   `call_waiter`: Solicita asistencia humana.
*   `request_bill`: Inicia el proceso de cierre de cuenta.
*   `open_menu`: Solicita ver la carta digital en el terminal.

---

## 4. Capa de Seguridad y Handshake
Antes de aceptar datos, el POS y el TablePad deben validar:
1.  **Token de Invitado:** Cifrado en el terminal y validado en el servidor.
2.  **Identidad de Mesa:** El terminal se identifica as\xc3\xad mismo al conectar.

> [!IMPORTANT]
> **Consistencia del JSON:** Independientemente de si usas el modo Nativo o el Bridge, el contenido del mensaje JSON **DEBE** seguir estrictamente la [Especificaci\xc3\xb3n T\xc3\xa9cnica Nativa](file:///home/kaber420/Documentos/proyectos/blackshot_iot/SPEC_NATIVE_JSON.md).
