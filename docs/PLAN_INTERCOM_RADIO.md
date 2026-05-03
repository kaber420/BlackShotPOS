# 📻 Plan: Blackshot Intercom (Radio Mode)

## 1. Visión General
Transformar la comunicación interna de la sucursal de mensajes de texto lentos a un sistema de **Radio/PTT (Push-To-Talk)**. El objetivo es permitir que el personal (baristas, meseros, cocina) se comunique instantáneamente mediante notas de voz que se reproducen automáticamente en todas las terminales, manteniendo un historial para consultas posteriores.

---

## 2. Arquitectura Técnica

### Backend (`pos_core/communications`)
- **Módulo Dedicado:** Crear carpeta `pos_core/communications` para lógica de mensajes.
- **Persistencia:** Base de datos SQLite para el historial de mensajes (quién, cuándo, qué tipo).
- **Almacenamiento de Audio:** Carpeta `uploads/intercom/` para guardar los fragmentos de voz (.webm o .ogg).
- **Real-Time:** Uso del tópico `"intercom"` en el `PubSubManager` existente para difusión instantánea.

### Frontend (`bs_frontend`)
- **Grabación:** Implementación de `MediaRecorder API` para capturar audio desde el navegador.
- **Reproducción Automática:** Al recibir un evento de tipo `voice_message`, el frontend disparará la reproducción del audio inmediatamente (si el usuario tiene la pestaña activa).
- **Gestión de Colas:** Si llegan dos audios seguidos, se encolan para no solaparse.

---

## 3. Experiencia de Usuario (UX)

### Componentes de Interfaz
- **Botón Flotante PTT:** Un botón de "Micrófono" que al mantener presionado cambia a rojo y muestra "GRABANDO...".
- **Indicador "ON AIR":** Cuando alguien está transmitiendo, todas las terminales muestran un aviso visual: "🎙️ [Nombre] hablando...".
- **Sidebar de Historial:** Un cajón lateral (Drawer) con la lista de audios del día, permitiendo repetir cualquier mensaje.

### Estética "Radio"
- **SFX (Sonidos):** 
    - *Beep-in:* Sonido corto de walkie-talkie al iniciar la recepción.
    - *Beep-out:* Sonido de estática corta al terminar.
- **Waveforms:** Visualización de ondas de audio en el historial para identificar rápidamente la duración y el volumen.

---

## 4. Fases de Implementación

### Fase 1: Infraestructura Base
- [ ] Crear modelo `IntercomMessage` y migración de BD.
- [ ] Implementar endpoint `POST /api/v1/pos/communications/voice` para recibir audios.
- [ ] Configurar el broadcast vía WebSockets al recibir el archivo.

### Fase 2: Componente Frontend
- [ ] Crear el `IntercomWidget.svelte`.
- [ ] Implementar lógica de grabación `startRecording/stopRecording`.
- [ ] Implementar el "Auto-Player" con efectos de sonido.

### Fase 3: Historial y Pulido
- [ ] Crear el Sidebar para ver mensajes pasados.
- [ ] Añadir filtros por canal (ej. General, Solo Cocina).
- [ ] Optimización de almacenamiento (borrado automático de audios antiguos).

---

## 6. Módulo Gateway: Enlace Híbrido (Radio Física)
Para empresas que ya usan Walkie-Talkies (FRS/GMRS), se implementará un nodo traductor que digitaliza el espectro radioeléctrico.

### Arquitectura del Nodo
1. **Hardware:** Raspberry Pi o PC con interfaz de audio USB conectada a un radio base.
2. **Software (Traductor):** Servicio ligero (Go/Python) que:
    - **Digitaliza el Aire:** Detecta audio en la entrada de línea y lo sube al servidor vía WebSockets.
    - **Transmite al Aire:** Recibe audio del servidor y lo saca por la tarjeta de sonido hacia el radio (usando VOX).

### Funciones Avanzadas
- **Indicador de Canal Ocupado:** Bloquea el botón PTT en la web si el nodo detecta que alguien está hablando físicamente por el radio.
- **Auditoría Total:** Todo lo que se habla por radio físico queda grabado y trackeado en el historial de Blackshot.
- **Ubicuidad:** La gerencia puede hablar a los radios físicos desde cualquier lugar del mundo a través de la interfaz web.
