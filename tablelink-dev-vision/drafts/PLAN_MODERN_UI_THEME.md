# Plan: Implementación de Interfaz Moderna (Layout Dashboard)

Este documento describe la estrategia para integrar una interfaz estilo "Automotive/Smart Dashboard" en el ecosistema Blackshot IoT, sin perder la compatibilidad con el diseño de lista clásico.

## 1. Filosofía de Diseño: ¿Compatibilidad o Sustitución?

**Decisión Técnica:** **Mantener Compatibilidad (Arquitectura Modular).**

No es necesario "destruir" el trabajo anterior. En el desarrollo de sistemas embebidos profesionales, es mejor manejar esto mediante **Layout Modes**. Esto permite que el mismo firmware funcione en:
- Pantallas pequeñas (2.8" - 3.5") en modo **LISTA**.
- Pantallas medianas/grandes (4.3"+) en modo **DASHBOARD**.

### Beneficios:
- **Modularidad:** El SDK de UI se vuelve más potente al ofrecer diferentes "skins".
- **A/B Testing:** Puedes mostrar ambos a los clientes y que ellos elijan.
- **Portabilidad:** Si el hardware cambia a una pantalla vertical, el modo lista sigue siendo útil.

## 2. Estrategia de Implementación como Tema

Manejaremos esto en dos capas:

### Capa A: El Tema (Colores y Estilos)
Crearemos un nuevo tema en `themes.h` llamado `BS_THEME_DASHBOARD_BLUE` inspirado en la imagen:
- **Fondo:** Azul marino profundo casi negro.
- **Acentos:** Cian brillante y Naranja vibrante para estados.
- **Cristal:** Opacidad de 180-200 con desenfoque simulado.

### Capa B: El Layout (Estructura de Objetos)
Refactorizaremos `DashboardView` para que el método `setup_screen` sea condicional:

```cpp
void DashboardView::setup_screen(lv_obj_t* parent) {
    #ifdef BS_LAYOUT_MODERN
        setup_modern_dashboard(parent);
    #else
        setup_classic_list(parent);
    #endif
}
```

## 3. Desglose de Componentes Modernos

### Sidebar (El "Mando de Control")
- Ubicado a la izquierda (aprox 60px de ancho).
- Iconos de alta resolución (SVG o fuentes personalizadas).
- Indicador visual de "sección activa" con un gradiente vertical.

### Grid Dinámico de Platos (Atomic Cards)
- En lugar de una lista que ocupa todo el ancho, usaremos `LV_FLEX_FLOW_ROW_WRAP`.
- Las tarjetas serán cuadradas o rectangulares pequeñas.
- **Efecto Ready:** Cuando un plato pase a "LISTO", la tarjeta tendrá un resplandor (Glow) cian palpitante.

### Widget de Estado (Información de la Mesa)
- Un área dedicada (esquina superior derecha) que resume la experiencia del cliente (Tiempo transcurrido, total acumulado, etc.).

## 4. Próximos Pasos

1. **Definir el nuevo tema** en `src/ui/themes.h`.
2. **Crear `setup_modern_dashboard`** en `src/UI/DashboardView.cpp`.
3. **Adaptar `create_dish_card`** para que detecte si está en modo dashboard y ajuste su tamaño/forma.

---
**¿Aprobado?** Si estás de acuerdo con no destruir la compatibilidad y usar este modo modular, procederé a crear el nuevo plan de implementación formal.
