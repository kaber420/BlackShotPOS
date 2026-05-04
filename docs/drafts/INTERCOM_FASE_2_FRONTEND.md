# 🎙️ Intercom Fase 2: Componentes Frontend y Audio Real-Time

Este documento detalla la implementación técnica de la interfaz de usuario para el sistema de Radio/PTT de Blackshot.

## 1. Objetivos
- Implementar la captura de audio en el navegador usando el codec **Opus**.
- Crear un widget flotante intuitivo para la comunicación entre áreas.
- Manejar la reproducción automática de mensajes entrantes (Modo Radio).

## 2. Componentes Técnicos

### A. Servicio de Audio (`lib/audio_service.ts`)
Encargado de la lógica de bajo nivel:
- `getMicrophoneStream()`: Solicita permisos y obtiene el stream.
- `startRecording()`: Inicia el `MediaRecorder` con `mimeType: 'audio/webm; codecs=opus'`.
- `stopRecording()`: Retorna un `Blob` de audio listo para enviar.

### B. Gestor de WebSockets (`lib/pos_socket.svelte.ts`)
Actualización para el tópico `intercom`:
```typescript
case 'intercom':
    const msg = data.data;
    // Si el modo es Live y el área coincide, reproducir inmediatamente
    if (intercomSettings.mode === 'Live' && (msg.is_global || msg.target_areas.includes(currentArea))) {
        playAudio(msg.audio_url);
    } else {
        // Guardar en la cola visual (Buzón)
        intercomMessages.update(m => [msg, ...m]);
    }
    break;
```

### C. IntercomWidget.svelte
Interfaz de usuario:
- **Botón PTT:** Cambia de color y escala al presionar/soltar.
- **Selector de Canales:** Tags visuales para marcar (Cocina, Barra, Todos).
- **Selector de Modo:** Toggle entre "Live" y "Inbox".

## 3. Desafíos de UX
- **Permisos de Audio:** Los navegadores a menudo bloquean el audio automático si el usuario no ha hecho click en la página. Se incluirá un "Overlay de Activación" si se detecta bloqueo.
- **Feedback Visual:** Uso de micro-animaciones (ondas) mientras se graba para confirmar que el micrófono está captando sonido.

## 4. Tareas
- [ ] Implementar `api/intercom.ts` para llamadas HTTP.
- [ ] Crear el widget en `lib/components/intercom/`.
- [ ] Integrar en el layout global.
- [ ] Pruebas de latencia entre terminales.
