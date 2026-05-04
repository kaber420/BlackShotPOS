# 🚀 Blackshot POS: Funciones de Grado Comercial

Este documento detalla las funciones necesarias para transformar Blackshot de un sistema operativo a una herramienta de gestión empresarial completa para restaurantes y cafeterías.

## 1. Motor de Descuentos y Reglas (Backend)
- **Tipos de Descuento:** 
    - Porcentual o monto fijo por ítem.
    - Descuento global a la cuenta (con motivo obligatorio).
- **Promociones Programadas:** Configurar reglas de "Happy Hour" (ej: Cerveza 2x1 de Lunes a Jueves, 18:00 a 20:00).
- **Cortesías:** Registro de consumos no cobrados por razones de relaciones públicas o errores de servicio, con log de auditoría.

## 2. Conciliación de Inventarios (Back-Office)
- **Conteo Físico:** Interfaz para que el administrador ingrese las existencias reales de insumos (ej: pesar el café, contar las leches).
- **Reporte de Varianza:** Comparación automática entre el stock teórico (según recetas vendidas) y el stock real.
- **Monetización de Pérdidas:** Calcular cuánto dinero representan los insumos faltantes no justificados.

## 3. Facturación Electrónica (Compliance)
- **Integración con PAC:** Conexión vía API para timbrado de facturas legales (XML/PDF).
- **Portal de Auto-factura:** Generación de un QR en el ticket de venta que permita al cliente facturar ingresando su RFC desde su propio dispositivo.

## 4. Business Intelligence (Analítica Avanzada)
- **Reporting Contable:** Exportación masiva de ventas, impuestos y gastos en formatos compatibles con softwares contables (CSV/Excel).
- **Análisis de Horas Pico:** Mapas de calor de ventas por hora y día para optimización de personal.

## 5. Control de Efectivo Multi-Caja
- **Arqueo Ciego:** El cajero declara el efectivo sin conocer la cifra del sistema para evitar ajustes manuales.
- **Gestión de Retiros Parciales (Cortes X):** Registro de retiros de efectivo durante el turno por seguridad.

## 6. CRM y Lealtad (Fidelización)
- **Perfiles de Cliente:** Historial de consumos, preferencias y fechas especiales (cumpleaños).
- **Monedero Electrónico:** Sistema interno de puntos o saldo prepagado para clientes frecuentes.
