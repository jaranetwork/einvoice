# Facturación SIFEN desde POS

## Introducción

El módulo POS de ERPNext puede generar facturas electrónicas SIFEN. Cuando la configuración del POS está en **Factura de Venta** (Sales Invoice), la factura se envía a SIFEN con `templateFactura = "ticket"` para impresión tipo ticket.

---

## Configuración Previa

### POS Settings

1. Ir a **POS Settings**
2. **Invoice Type**: seleccionar `Factura de Venta` (Sales Invoice)
3. En **POS Additional Fields**: agregar el campo **Tipo de Transacción** (Select) para que `sifen_tipo_transaccion` esté disponible en POS
4. Guardar

### POS Profile

1. Ir a **POS Profile** → **Add POS Profile**
2. Completar datos generales (nombre, warehouse, etc.)
3. En **SIFEN Código Punto de Expedición**: ingresar 3 dígitos (ej: `001`)
4. Guardar

---

## Flujo en POS

| Paso | Acción | Detalle |
|------|--------|---------|
| 1 | Abrir **Point of Sale** | |
| 2 | Seleccionar **perfil POS** configurado | |
| 3 | Seleccionar **tipo de pago** | Ej: Efectivo, Tarjeta |
| 4 | Click en **Abrir Caja** | |
| 5 | Seleccionar **Cliente** | Cliente con campos SIFEN configurados |
| 6 | Agregar **Productos** | Items con Item Tax Template |
| 7 | Click en **Pedido** | Se crea la factura en estado Borrador |
| 8 | Click en **Campos Adicionales** y seleccionar **Tipo de Transacción SIFEN** | Ej: `1|Venta de mercadería` |
| 9 | En la nueva sección, click en **Pedido Completo** | Se valida la factura (submit) → se ejecuta `validar_sifen_tipo_transaccion` |
| 10 | En la sección de resumen (última), click en **Generate E-Invoice** | Envía a SIFEN |
| 11 | Esperar notificación de **Aceptado** | Real‑time desde el servidor |
| 12 | Click en **Print E-Invoice** | Se abre ventana de impresión para el KUDE tipo ticket |

> **Nota:** El botón **Print E-Invoice** aparece automáticamente cuando `custom_sifen_factura_id` tiene valor.
> No requiere esperar a que el estado sea "Aceptado", pero se recomienda esperar la notificación.

---

## Comportamiento del template

| Escenario | `templateFactura` |
|-----------|-------------------|
| POS Invoice | `"ticket"` |
| Sales Invoice con `Incluir Pago (POS)` activado (`is_pos = True`) | `"ticket"` |
| Sales Invoice normal (sin POS) | `"normal"` |

---

## Referencias

- [Configuración del Cliente](04_customer_setup.md)
- [Configuración de Items](05_items_setup.md)
- [API SIFEN](07_sifen_api.md)
- [Flujo de Trabajo](08_workflow.md)
- [Solución de Problemas](09_troubleshooting.md)

---

**Última actualización:** 2026-06-10
