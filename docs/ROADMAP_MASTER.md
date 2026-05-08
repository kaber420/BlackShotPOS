# 🗺️ Roadmap Maestro: Evolución Blackshot POS

Este documento unifica la visión estratégica y operativa para transformar Blackshot en un sistema de gestión de grado comercial. Combina mejoras lógicas, control interno y gestión de personal.

---

## 1. Integridad Financiera y Saldo (P0)
*Objetivo: Mejorar la precisión de los reportes y control de flujo.*

- **Dashboard de Auditoría Avanzado:**
    - Visualización de cancelaciones y motivos detallados.
    - Registro de ediciones post-pago (si se permiten).

---

## 2. Gestión de Personal y Permisos Granulares (P1)
*Objetivo: Controlar quién puede hacer qué y medir su desempeño.*

- [x] **Roles como Presets + Overrides:**
    - [x] Implementar presets de permisos por rol (admin, manager, waiter, kitchen).
    - [x] Almacenar permisos individuales en el JSON de `metadata` del usuario para casos excepcionales (ej. un mesero que sí puede cobrar).
- [x] **Recetario Markdown:** 
    - [x] Instrucciones de preparación visibles en el KDS para estandarizar la calidad.
    - [x] Soporte de renderizado Markdown para procedimientos complejos.
- [x] **Métricas de Productividad:**
    - [x] Reportes de ventas por mesero/barista.
    - [x] Tiempos promedio de preparación en el KDS para medir eficiencia en cocina.
- [ ] **Control de Acceso (Clock-in/out):**
    - [ ] Registro de asistencia mediante PIN directamente en el POS.

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

## 4. Eficiencia Operativa y Hardware (P2)
*Objetivo: Velocidad, precisión y conexión con el mundo físico.*

- **Control de Tiempos (Hold & Fire):** Permitir que el mesero marque ítems para "retener" (Hold) y enviarlos a cocina manualmente cuando el cliente esté listo (Fire).
- **Comunicación Interna (Radio Mode):** 
    - Implementar sistema de comunicación por voz tipo PTT (Push-to-talk).
    - **Híbrido Radio-Gateway:** Enlace con walkie-talkies físicos mediante hardware (Raspberry Pi/Nodo).
- **Integración de Básculas Digitales:**
    - Uso de **Web Serial API** para lectura directa de peso desde básculas digitales comerciales vía RS232/USB.
    - Soporte para productos "Pesados" con cálculo de precio dinámico en el carrito.
- **Etiquetado de Producción:** Generación de etiquetas (labels) para vasos con modificadores detallados.

---

## 5. UI/UX e Inventario Avanzado (P1)
*Objetivo: Versatilidad en la gestión y soporte para hardware de escaneo.*

- **Soporte de Identificadores (SKU/Barcodes):**
    - Implementación de campo SKU en Productos e Ingredientes.
    - Soporte para escaneo de códigos de barras en POS y recepción de mercancía.
- **Vistas Duales (Cuadros vs. Lista):** 
    - Implementar toggle de visualización en el catálogo (Vista de botones para ventas rápidas vs. Vista de tabla para administración/inventario).
- **Gestión Avanzada de Inventario:**
    - **Control por Lotes (Batches):** Seguimiento de caducidades y lotes de entrada (FIFO/FEFO).
    - **Edición Masiva (Bulk Update):** Herramienta para actualizar múltiples items (precios, stock, categorías) de manera simultánea.
- **Arquitectura Dirigida por Eventos (P1):** Ver [Especificación EDA](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/docs/ARCHITECTURE_EVENT_DRIVEN.md)
    - [ ] **Global Persistence Worker (GPW):** Implementación del "músculo" de escritura serializada para garantizar integridad total.
    - [ ] **Refactorización de Ventas (RFC-003):** Migración de Ventas al modelo de "Emisión Pura", eliminando todas las importaciones circulares de Inventario y Mesas. Ver [EVOLUTION_SALES.md](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/docs/EVOLUTION_SALES.md)
    - [ ] **Inventory & Table Processors:** Implementación de los listeners que reaccionan a ventas para gatillar stock y estados de mesa vía GPW.

## 5. Ecosistema IoT y Experiencia de Cliente (P2)
*Objetivo: Empoderar al cliente y digitalizar la mesa.*

- **TableLink (TablePad IoT):** 
    - Despliegue de dispositivos ESP32-S3 por mesa para visualización dinámica del estado de la orden ("EN COLA", "PREPARANDO", "LISTO").
    - Acciones directas desde la mesa: Llamar Mesero, Solicitar Cuenta y Feedback.
    - Sincronización bidireccional en tiempo real con el POS central.

---

## 6. Resiliencia y Escalabilidad (P3)
- **Modo Offline Local-First:** Sincronización inteligente de pedidos cuando falle el internet.
- **Aislamiento Multi-tenancy:** Preparar la arquitectura para soportar múltiples organizaciones independientes (si se decide escalar a SaaS).
