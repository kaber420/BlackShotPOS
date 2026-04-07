# Roadmap de Desarrollo: Blackshot POS

Este documento es nuestra única fuente de verdad para la evolución del sistema. Captura la arquitectura deseada y las reglas de negocio acordadas para futuras implementaciones.

---

## 🚀 Fase 1: Recetas e Inventario Inteligente (Inventory Deep-Sync)
**Objetivo**: Automatizar el control de existencias basado en lo que se vende.

*   **Receta por Producto**: Definir exactamente cuántos gramos de café, ml de leche o unidades consume cada producto de la materia prima.
*   **Descuento Automático**: Al confirmar una venta (status PAID/PREPARING), el sistema restará los ingredientes del inventario.
*   **Gestión de Costos**: Cálculo del costo de producción basado en el precio actual de los ingredientes.

## 🖼️ Fase 2: Interfaz de Creación de Productos (Admin UX)
**Objetivo**: Facilitar la carga de datos y multimedia.

*   **Workflow Unificado**: Interfaz paso a paso para crear productos con descripción, fotos y recetas.
*   **Carga de Imágenes**: Soporte para subir archivos directamente desde la computadora con previsualización.
*   **Administración de Medidas**: Interfaz tipo "categoría" para crear y gestionar nombres propios de tamaños.

## 📏 Fase 3: Soporte Multitalla y Precios Fijos (Advanced Variants)
**Objetivo**: Manejar tamaños con nombres creativos (Venti, Grande) y precios independientes.

*   **Medidas Personalizables**: Creación de tallas con:
    - **Nombre**: "Chico", "Mega", "Venti", etc.
    - **Especificación**: Valor numérico y unidad (ej: 20 oz, 500 ml).
*   **Arquitectura de Variantes**: Un producto (ej: Latte) puede tener múltiples variantes ligadas a una medida.
*   **Precios Fijos por Medida**: Cada variante tendrá su propio precio final asignado manualmente (sin cálculos de extras).
*   **Recetas por Variante**: Cada tamaño tendrá su propia cantidad de ingredientes (ej: un Latte Grande consumirá más leche que uno Chico).

## ☕ Fase 4: Modificadores y Personalización (The Coffee Experience)
**Objetivo**: Personalización granular por el cliente.

*   **Grupos de Modificadores**: Categorías como "Leches", "Jarabes", "Toppings".
*   **Opciones Obligatorias vs. Opcionales**: Elegir leche (Obligatorio) vs. elegir jarabe (Opcional).
*   **Precios de Modificadores**: Definir si un extra (ej: Soya) tiene costo adicional o es gratuito.

## 🛒 Fase 5: Experiencia POS (Frontend Magic)
**Objetivo**: Rapidez y precisión para el cajero.

*   **Modal Dinámico**: Al seleccionar un café, saltará un modal para elegir:
    1. Tamaño (Botones grandes).
    2. Modificadores (Leches/Extras).
*   **Suma de Precios**: El cajero verá el precio final antes de confirmar.
*   **Alertas de Stock**: El sistema avisará si un ingrediente de la receta o de un modificador está agotado.

## 🥗 Fase 6: Información Nutricional (Modo Fit / Estimaciones)
**Objetivo**: Transparencia nutricional simplificada.

*   **Estimaciones Manuales**: Ingresar manualmente los gramos de proteína, carbohidratos, grasas y calorías por cada variante/tamaño.
*   **Modo Simple**: Evitar cálculos complejos por ingrediente; el administrador pone los números estimados directamente en la receta.
*   **Visualización en POS**: Mostrar estos datos para ayudar a clientes con dietas específicas.

## 📄 Fase 7: Reportes y Alertas
**Objetivo**: Control total y auditoría.

*   **Alertas de Bajo Stock**: Notificaciones cuando ingredientes críticos (café, leche) bajen del nivel mínimo.
*   **Análisis de Margen**: Reportes de cuánto dinero ganamos por producto tras restar el costo de materia prima.

---
> **Nota**: Este roadmap documenta la planeación estratégica. No se han implementado cambios en el código funcional durante esta sesión por seguridad y control del usuario.
