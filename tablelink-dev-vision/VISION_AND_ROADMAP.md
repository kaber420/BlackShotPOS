# Visión, Arquitectura y Roadmap: Blackshot IoT
**Concepto:** El Estándar Open-Source para el Restaurante Inteligente

Este documento consolida la visión estratégica, la arquitectura técnica y el camino a seguir para convertir a **Blackshot IoT** en la plataforma líder para la democratización de tecnología en mesa.

---

## 1. Misión y Pilares Estratégicos
Nuestra misión es dotar de inteligencia a los objetos físicos que ya existen en la mesa del comensal (servilleteros, robots, menús), permitiendo una comunicación fluida y elegante entre el cliente y el sistema de gestión.

### Pilares:
*   **Libertad de Hardware:** Basado en componentes estándar (ESP32-S3) y fabricación local mediante **impresión 3D de resina**.
*   **Código para Todos:** Soporte multi-lenguaje (C++, MicroPython, Web) para eliminar la barrera de entrada a colaboradores.
*   **Arquitectura Desacoplada:** POS-Agnóstico mediante un servidor puente (**Bridge**) que unifica cualquier API externa.

---

## 2. Arquitectura del Ecosistema

### Niveles de Dispositivos (Tier System)
1.  **Tier 1: Nodos Empotrados (ESP32-S3):** Dispositivos de bajísimo costo y consumo para ser incrustados en artículos inteligentes (servilleteros, robots). Utilizan **LVGL** para alto rendimiento.
2.  **Tier 2: Terminales de Alto Rendimiento (Raspberry Pi Zero 2W / Similares):** Dispositivos potentes dedicados que permiten ejecutar **Interfaces Web Completas**. Ideal para kioscos o menús interactivos donde se busca una facilidad de desarrollo máxima para la comunidad sin los riesgos de seguridad y robo asociados a tablets Android comerciales.

### El "Blackshot Bridge"
Un middleware (Python/Node) que:
- Normaliza datos de cualquier POS (Toast, Clover, Square, etc.) al **Protocolo Unificado Blackshot**.
- Soporta **Custom Fields** para enviar datos específicos sin cambiar el firmware del terminal.
- **Seguridad Dinámica:** Si el terminal sale de la red del local, entra en modo **Cactus** permanentemente, haciendo el hardware inservible fuera de su propósito.

---

## 3. Propuesta de Funcionalidades (Cliente en Mesa)
*   **Interacción:** Menú digital interactivo, modificación de pedido directo y pago mediante QR dinámico.
*   **Servicio:** Botones de acción crítica (Faltan servilletas, llamar limpieza, pedir cuenta).
*   **Engagement:** Mini-juegos de espera, storytelling de marca y encuestas rápidas de satisfacción.

---

## 4. Entorno de Ingeniería: Blackshot IoT Studio
El "Digital Twin Lab" permite simular el producto final en un entorno web antes de su fabricación física:
- **Mockup Overlay:** Visualiza el código C++/LVGL operando dentro de una imagen real del producto.
- **Stress Testing:** Simulación de fallos de red (Offline/Cactus Mode) para validar la resiliencia.

---

## 5. Hoja de Ruta (Roadmap 2026)

### Fase 1: Cimientos y API (Q2 2026) - *EN PROGRESO*
*   Definición del **API Protocol v1.0**.
*   Lanzamiento del **IoT Studio** con mockups base.
*   Implementación de resiliencia de conexión.

### Fase 1.5: Pulido de UI y Branding (Q2-Q3 2026)
*   Soporte para **Miniaturas Dinámicas** (JPG optimizado) en tarjetas de platillos.
*   Implementación de **Splash Screens** con logos de marca de carga instantánea.
*   Sistema de **Avisos Animados (GIFs)** ligeros para notificaciones y mascota del negocio.
*   Visualización enriquecida de productos (Tallas/Medidas, extras y notas detalladas).

### Fase 2: Hardware y Comunidad (Q3 2026)
*   Publicación de la **Especificación Gold Standard** (Hardware Spec).
*   Catálogo de modelos STL para impresión 3D (Servilletero y Robot).
*   Lanzamiento del **Bridge SDK** para nuevos adaptadores de POS.

### Fase 3: Ecosistema Extendido (Q4 2026)
*   Soporte oficial para **MicroPython + LVGL**.
*   Módulo de Kiosco Web integrado en el Bridge.
*   Marketplace comunitario de temas y diseños 3D.

---

Este es un proyecto bajo licencia **AGPLv3**. La tecnología debe ser libre, auditable y accesible para todos.
