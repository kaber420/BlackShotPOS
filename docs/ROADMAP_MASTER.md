# 🗺️ Roadmap Maestro: Evolución Blackshot POS

Este documento unifica la visión estratégica y operativa para transformar Blackshot en un sistema de gestión de grado industrial. Combina mejoras lógicas, control interno y gestión de personal.

---

## 1. Integridad Financiera y Saldo (P0)
*Objetivo: Mejorar la precisión de los reportes y control de flujo.*

- **Dashboard de Auditoría Avanzado:**
    - Visualización de cancelaciones y motivos detallados.
    - Registro de ediciones post-pago (si se permiten).

---

## 2. Gestión de Personal y Permisos Granulares (P1)
*Objetivo: Controlar quién puede hacer qué y medir su desempeño.*

- **Roles como Presets + Overrides:**
    - Implementar presets de permisos por rol (admin, manager, waiter, kitchen).
    - Almacenar permisos individuales en el JSON de `metadata` del usuario para casos excepcionales (ej. un mesero que sí puede cobrar).
- **Recetario Markdown:** 
    - Instrucciones de preparación visibles en el KDS para estandarizar la calidad.
    - Soporte de renderizado Markdown para procedimientos complejos.
- **Métricas de Productividad:**
    - Reportes de ventas por mesero/barista.
    - Tiempos promedio de preparación en el KDS para medir eficiencia en cocina.
- **Control de Acceso (Clock-in/out):**
    - Registro de asistencia mediante PIN directamente en el POS.

---

## 3. Control Interno y Caja Chica (P1)
*Objetivo: Evitar "robos hormiga" y descuadres de efectivo.*

- **Módulo de Gastos (Caja Chica):** 
    - Registro de salidas de efectivo desde el POS (proveedores, limpieza, emergencias).
    - Cálculo: `Efectivo Esperado = Fondo Inicial + Ventas Efectivo - Gastos`.
- **Cruce de Inventarios (Teórico vs. Real):**
    - Comparar el consumo según recetas contra el conteo físico.
    - Generar reportes de variación monetizada.
- **Registro de Merma (Waste):**
    - Funcionalidad para descontar stock por caducidad o errores sin pasar por ventas.

---

## 4. Eficiencia Operativa y UX (P2)
*Objetivo: Velocidad y precisión en el servicio.*

- **Control de Tiempos (Hold & Fire):** Permitir que el mesero marque ítems para "retener" (Hold) y enviarlos a cocina manualmente cuando el cliente esté listo (Fire).
- **Hardware Inteligente:** Integración de básculas y generación de etiquetas (labels) para vasos con modificadores.

---

## 5. Resiliencia y Escalabilidad (P3)
- **Modo Offline Local-First:** Sincronización inteligente de pedidos cuando falle el internet.
- **Aislamiento Multi-tenancy:** Preparar la arquitectura para soportar múltiples organizaciones independientes (si se decide escalar a SaaS).
