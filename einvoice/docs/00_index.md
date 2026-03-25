# E-Invoice Module Documentation

Documentación completa del módulo E-Invoice para integración con SIFEN (Sistema Integrado de Facturación Electrónica Nacional) de Paraguay.

## Índice de Documentos

1. [Guía de Inicio Rápido](01_quick_start.md) - Instalación y configuración básica
2. [Campos SIFEN](02_sifen_fields.md) - Mapeo de campos ERPNext → SIFEN
3. [Configuración de la Empresa](03_company_setup.md) - Campos obligatorios en Company
4. [Configuración del Customer](04_customer_setup.md) - Campos obligatorios en Customer
5. [Configuración de Items](05_items_setup.md) - Item Tax Template y SIFEN Tipo IVA
6. [Validaciones](06_validations.md) - Validaciones automáticas al guardar/validar
7. [API SIFEN](07_sifen_api.md) - Estructura del payload y endpoints
8. [Flujo de Trabajo](08_workflow.md) - Proceso completo de facturación
9. [Solución de Problemas](09_troubleshooting.md) - Errores comunes y soluciones
10. [Referencia Técnica](10_technical_reference.md) - Estructura de archivos y funciones

---

## Descripción General

El módulo **E-Invoice** permite la integración de ERPNext v15 con campos requeridos del sistema **SIFEN** de la SET (Subsecretaría de Estado de Tributación) de Paraguay para la emisión de facturas electrónicas.

### Características Principales

- ✅ Generación automática de facturas electrónicas
- ✅ Validación de campos requeridos antes del envío
- ✅ Mapeo automático de datos ERPNext → SIFEN
- ✅ Soporte para todos los tipos de operación (B2B, B2C, B2G, B2F)
- ✅ Cálculo automático de tipoOperacion y tipoImpuesto
- ✅ Validación de Payment Terms según SIFEN
- ✅ Descarga de XML y KUDE desde Sales Invoice

### Requisitos

- ERPNext v15
- Frappe Framework v15
- MariaDB 11.8
- Conexión a API FEPY
- Timbrado habilitado

### Estructura del Módulo

```
einvoice/
├── e_invoice/
│   ├── custom/                      # Custom Fields (JSON)
│   │   ├── company_*.json           # Campos para Company
│   │   ├── customer_*.json          # Campos para Customer
│   │   ├── address_*.json           # Campos para Address
│   │   └── sales_invoice_*.json     # Campos para Sales Invoice
│   ├── doctype/                     # DocTypes personalizados
│   │   └── e_invoice_actividad_economica/
│   ├── utils/
│   │   └── api_client.py            # Lógica principal de SIFEN
│   ├── doc_events/
│   │   └── sales_invoice.py         # Eventos de Sales Invoice
│   ├── public/
│   │   └── js/
│   │       └── sales_invoice_combined.js  # Botones y UI
│   ├── install.py                   # Script de instalación
│   └── hooks.py                     # Configuración de hooks
└── docs/                            # Esta documentación
```

---

## Quick Reference

### Campos Obligatorios por Entidad

| Entidad | Campos Obligatorios |
|---------|-------------------|
| **Company** | RUC, Timbrado, Actividades Económicas, Responsable SIFEN |
| **Customer** | sifen_tipo_documento, sifen_tipo_impuesto |
| **Address** | Departamento, Distrito, Ciudad, Número de Casa |
| **Item** | Item Tax Template con sifen_tipo_iva |
| **Sales Invoice** | Payment Terms (si es crédito), Número de Control |

### Tipos de Operación SIFEN

| Código | Tipo | Descripción |
|--------|------|-------------|
| 1 | B2B | Business to Business |
| 2 | B2C | Business to Consumer |
| 3 | B2G | Business to Government |
| 4 | B2F | Business to Foreigner |

### Tipos de Impuesto SIFEN

| Código | Tipo | Descripción |
|--------|------|-------------|
| 1 | IVA | Cliente local contribuyente |
| 2 | ISC | Productos con impuesto selectivo |
| 3 | Renta | Cliente extranjero B2F con RUC |
| 4 | Ninguno | Cliente extranjero sin RUC |
| 5 | IVA-Renta | Mixto |

### Afectación al IVA (Items)

| Código | Tipo | Descripción |
|--------|------|-------------|
| 1 | Gravado | Item con IVA (10%) |
| 2 | Exonerado | Art.83 - Ley 125/91 |
| 3 | Exento | No IVA |
| 4 | Parcial | Gravado parcial |

---

## Soporte

Para reportar errores o solicitar funcionalidades adicionales, por favor contactar al equipo de desarrollo.

**Última actualización:** 2026-03-25
**Versión del módulo:** 1.0.0
**ERPNext compatible:** v15
