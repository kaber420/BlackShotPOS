# 📻 Plan: Blackshot Intercom (Radio Mode)

## 1. Visión General
Transformar la comunicación interna de la sucursal de mensajes de texto lentos a un sistema de **Radio/PTT (Push-To-Talk)**. El objetivo es permitir que el personal se comunique instantáneamente mediante fragmentos de voz (Opus) dirigidos a canales específicos o globales.

---

## 2. Modos de Operación (Escucha)

Para evitar interrumpir en momentos críticos o en áreas ruidosas, cada terminal podrá configurar su **Modo de Escucha**:

| Modo | Nombre | Comportamiento |
| :--- | :--- | :--- |
| 🔈 **Live** | **Radio en Vivo** | El audio se reproduce automáticamente apenas llega. Ideal para Cocina/Barra. |
| 🔇 **Inbox** | **Modo Buzón** | Solo muestra una notificación visual. El usuario debe pulsar "Play" manualmente. |
| 🔕 **Muted** | **Silencio** | No reproduce ni notifica, solo guarda en el historial. |

---

## 3. Canales y Direccionamiento

El sistema no enviará todo a todos por defecto. Se segmentará por **Canales de Área**:

- **Canales Automáticos:** Basados en las `Production Areas` existentes (Cocina, Barra, Caja, Administración).
- **Canal Global (General):** Envía el mensaje a todas las terminales de la sucursal.
- **Selección Múltiple:** El emisor puede marcar varios canales antes de hablar (ej. Cocina + Barra).

---

## 4. Arquitectura Técnica

### Backend (`pos_core/communications`)
- **Modelos:** 
    - `IntercomMessage`: Almacena meta-datos (emisor, timestamp, archivo_path).
    - `IntercomChannel`: Tabla intermedia para direccionar mensajes a N áreas.
- **Real-Time:** Los eventos de WebSocket llevarán el campo `target_areas: []`. El frontend decidirá si reproducir según su configuración local.

### Frontend (`bs_frontend`)
- **Grabación:** `MediaRecorder` con `audio/webm; codecs=opus`.
- **Lógica de Filtro:** 
    - Si `terminal.area` está en `message.target_areas` OR `message.is_global`:
        - Si `config.mode == 'Live'`: Play().
        - Si `config.mode == 'Inbox'`: Mostrar Badge de "Nuevo Mensaje".

---

## 5. Experiencia de Usuario (UX)

### Componente PTT (Push-To-Talk)
- **Selector de Canal:** Un pequeño dropdown o tags sobre el botón de micro para elegir a quién hablar.
- **Feedback Visual:**
    - Al grabar: Círculo pulsante rojo.
    - Al recibir: Animación de ondas (Waveform) activa.

---

## 6. Fases de Implementación

### Fase 1: Infraestructura y Canales
- [ ] Crear modelos `IntercomMessage` y relaciones con `ProductionArea`.
- [ ] Endpoint `POST /api/v1/pos/communications/voice` con soporte para `channel_ids`.

### Fase 2: El Widget Intercom
- [ ] Implementar `IntercomWidget.svelte` con selector de modo (Live/Inbox).
- [ ] Lógica de grabación y envío.
- [ ] Sistema de colas de reproducción (para que dos audios no suenen a la vez).

### Fase 3: Gateway y Pulido
- [ ] Historial con mini-reproductor y ondas.
- [ ] (Opcional) Integración con radios físicos (Gateway).

---

## 7. Módulo Gateway: Enlace Híbrido (Radio Física)
*(Mantenido para futura expansión)*
Integración vía Raspberry Pi para digitalizar el aire de radios walkie-talkie analógicos y subirlos a los canales de Blackshot.

