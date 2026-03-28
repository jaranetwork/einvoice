# Referencia Técnica

Este documento proporciona una referencia técnica completa del módulo E-Invoice.

---

## Estructura de Archivos

```
einvoice/
├── __init__.py
├── hooks.py                          # Configuración de hooks
├── e_invoice/
│   ├── __init__.py
│   ├── custom/                       # Custom Fields (JSON)
│   │   ├── address_numero_casa.json
│   │   ├── address_sifen_buttons.json
│   │   ├── company_01_sifen_campos_obligatorios.json
│   │   ├── company_02_codigo_establecimiento.json
│   │   ├── company_03_codigo_punto_expedicion_default.json
│   │   ├── company_04_sifen_column_1.json
│   │   ├── company_05_numero_timbrado.json
│   │   ├── company_06_fecha_timbrado.json
│   │   ├── company_07_sifen_denominacion.json
│   │   ├── company_08_sifen_column_2.json
│   │   ├── company_09_tipo_contribuyente.json
│   │   ├── company_10_tipo_regimen.json
│   │   ├── company_11_sifen_responsable.json
│   │   ├── company_12_actividades_economicas.json
│   │   ├── company_13_section_cierre.json
│   │   ├── customer_contribuyente.json
│   │   ├── customer_sifen_tipo_documento.json
│   │   ├── customer_sifen_tipo_impuesto.json
│   │   ├── pos_profile_codigo_punto_expedicion.json
│   │   ├── sales_invoice_einvoice_fields.json
│   │   └── sales_invoice_einvoice_tab.json
│   ├── doctype/                      # DocTypes personalizados
│   │   └── e_invoice_actividad_economica/
│   │       ├── __init__.py
│   │       └── e_invoice_actividad_economica.json
│   ├── utils/
│   │   ├── __init__.py               # Exporta todas las funciones públicas
│   │   ├── address_validation.py     # Validación de Address
│   │   ├── api_client.py             # Lógica principal SIFEN y API
│   │   └── utils.py                  # Funciones auxiliares
│   ├── builders/                     # Constructores de payload SIFEN
│   │   ├── __init__.py
│   │   ├── data_builder.py           # Construye sección DATA
│   │   ├── param_builder.py          # Construye sección PARAM
│   │   ├── cliente_builder.py        # Construye sección cliente
│   │   ├── items_builder.py          # Construye sección items
│   │   └── condicion_builder.py      # Construye sección condición
│   ├── validators/                   # Validadores SIFEN
│   │   ├── __init__.py
│   │   └── payment_validator.py      # Valida términos de pago
│   ├── doc_events/
│   │   ├── __init__.py
│   │   └── sales_invoice.py          # Eventos de Sales Invoice
│   ├── public/
│   │   ├── js/
│   │   │   └── sales_invoice_combined.js  # Botones y UI
│   │   └── css/
│   │       └── (si aplica)
│   ├── workspace/
│   │   └── e_invoice.json            # Workspace definition
│   ├── before_install.py             # Pre-install cleanup
│   └── install.py                    # Post-install setup
└── docs/                             # Documentación
    ├── 00_index.md
    ├── 01_quick_start.md
    ├── 02_sifen_fields.md
    ├── 03_company_setup.md
    ├── 04_customer_setup.md
    ├── 05_items_setup.md
    ├── 06_validations.md
    ├── 07_sifen_api.md
    ├── 08_workflow.md
    ├── 09_troubleshooting.md
    └── 10_technical_reference.md
```

---

## Hooks Configuration

### hooks.py

```python
# Installation
before_install = "einvoice.e_invoice.before_install.before_install"
after_install = "einvoice.e_invoice.install.after_install"
before_uninstall = "einvoice.e_invoice.install.before_uninstall"

# Document Events
doc_events = {
    "Address": {
        "validate": "einvoice.e_invoice.utils.address_validation.validate_address_sifen",
    },
    "Sales Invoice": {
        "validate": [
            "einvoice.e_invoice.utils.api_client.asignar_numero_control",
            "einvoice.e_invoice.utils.api_client.validar_campos_sifen",
        ],
    }
}

# Doctype JS
doctype_js = {
    "Sales Invoice": "e_invoice/public/js/sales_invoice_combined.js",
    "Address": "e_invoice/doctype/address/address.js"
}

# Doctype Python
doctype_python = {
    "Address": "e_invoice.doctype.address.address"
}
```

---

## Funciones Principales

### api_client.py

#### Funciones de Validación

| Función | Descripción | Evento |
|---------|-------------|--------|
| `validar_campos_sifen(doc, method)` | Valida todos los campos SIFEN | validate |
| `asignar_numero_control(doc, method)` | Genera número de control único | validate |

#### Funciones de API

| Función | Descripción | Retorna |
|---------|-------------|---------|
| `send_invoice_to_external_api(sales_invoice)` | Envía factura a API SIFEN | dict {success, message, data} |
| `get_invoice_status(factura_id)` | Consulta estado en SIFEN | dict {success, data} |
| `download_sifen_file(factura_id, file_type, invoice_name)` | Descarga XML/KUDE | dict {file_content, filename, content_type} |
| `download_xml(factura_id, invoice_name)` | Descarga XML (wrapper) | dict {file_content, filename, content_type} |
| `download_pdf(factura_id, invoice_name)` | Descarga KUDE PDF (wrapper) | dict {file_content, filename, content_type} |
| `test_api_connection()` | Prueba conexión con API SIFEN | dict {success, message} |

#### Funciones de Construcción de Payload

| Función | Descripción | Retorna |
|---------|-------------|---------|
| `prepare_invoice_data(sales_invoice)` | Construye payload completo | dict {param, data} |
| `build_param_section(company)` | Construye sección param | dict |
| `build_data_section(...)` | Construye sección data | dict |
| `build_cliente_section(...)` | Construye sección cliente | dict |
| `build_items_data(sales_invoice, moneda)` | Construye array de items | list |
| `build_condicion_section(...)` | Construye sección condición | dict |

### utils.py - Funciones Auxiliares

| Función | Descripción | Retorna |
|---------|-------------|---------|
| `get_paraguay_location_codes(state, county, city, country)` | Obtiene códigos de ubicación PY | dict {departamento, distrito, ciudad, ...} |
| `get_country_codes(customer_country)` | Obtiene código de país | tuple (codigo, nombre) |
| `get_company_address(company)` | Obtiene dirección de empresa | dict |
| `get_usuario_from_invoice(sales_invoice)` | Obtiene usuario de factura | dict |
| `get_actividades_economicas(company)` | Obtiene actividades económicas | list |
| `get_timbrado_info(company)` | Obtiene info de timbrado | tuple |
| `get_tipo_contribuyente(company)` | Obtiene tipo de contribuyente | int |
| `get_tipo_regimen(company)` | Obtiene tipo de régimen | int |
| `get_condicion_operacion(sales_invoice)` | Determina contado/crédito | int (1-2) |
| `get_condicion_entregas(...)` | Construye entregas de pago | list |
| `get_credito_info(sales_invoice)` | Obtiene info de crédito | dict |
| `get_indicador_presencia(sales_invoice)` | Determina presencia indicator | int (1-4) |
| `get_tipo_transaccion(sales_invoice)` | Determina tipo de transacción | int (1-13) |
| `get_condicion_anticipo(sales_invoice)` | Determina condición de anticipo | int (1-2) |
| `get_sifen_tipo_impuesto(sales_invoice)` | Obtiene tipo de impuesto | tuple (tipo, rate) |
| `get_sifen_unidad_medida(stock_uom)` | Mapea UOM a código SIFEN | int |
| `generar_numero_control(company)` | Genera código único de 9 dígitos | string |
| `clean_html(html_string)` | Limpia HTML | string |
| `download_pdf_file(factura_id)` | Descarga PDF (legacy) | dict |
| `download_xml_file(factura_id)` | Descarga XML (legacy) | dict |

### address_validation.py

| Función | Descripción | Retorna |
|---------|-------------|---------|
| `validate_address_sifen(doc, method)` | Valida campos SIFEN en Address | None |

### builders/data_builder.py

| Función | Descripción | Retorna |
|---------|-------------|---------|
| `build_data_section(...)` | Construye sección DATA completa | dict |
| `prepare_invoice_data(sales_invoice)` | Prepara payload completo | dict {param, data} |
| `_build_documento_asociado(sales_invoice, tipo_documento)` | Construye documento asociado (NC/ND) | list |
| `_build_nota_credito_debito(sales_invoice, tipo_documento)` | Construye sección NC/ND | dict |

---

## Custom Fields

### Company Fields

| Fieldname | Fieldtype | Label | Descripción |
|-----------|-----------|-------|-------------|
| `codigo_establecimiento` | Data | Código de Establecimiento | 3 dígitos |
| `codigo_punto_expedicion_default` | Data | Código Punto de Expedición | 3 dígitos |
| `numero_timbrado` | Data | Número de Timbrado | Timbrado SET |
| `fecha_timbrado` | Date | Fecha de Timbrado | Fecha timbrado |
| `tipo_contribuyente` | Select | Tipo de Contribuyente | 1=Física, 2=Jurídica |
| `tipo_regimen` | Select | Tipo de Régimen | 1-8 |
| `sifen_denominacion` | Data | Denominación | Nombre establecimiento |
| `sifen_responsable_tipo_documento` | Select | Tipo Documento Responsable | 1-4 |
| `sifen_respons_numero_documento` | Data | Número Documento Responsable | Número |
| `sifen_responsable_nombre` | Data | Nombre Responsable | Nombre completo |
| `sifen_responsable_cargo` | Data | Cargo Responsable | Cargo |
| `actividades_economicas` | Table | Actividades Económicas | Child table |

### Customer Fields

| Fieldname | Fieldtype | Label | Descripción |
|-----------|-----------|-------|-------------|
| `sifen_contribuyente` | Check | Es contribuyente? | Boolean |
| `sifen_tipo_documento` | Select | SIFEN Tipo Documento | 1-4 |
| `sifen_tipo_impuesto` | Select | SIFEN Tipo Impuesto | 1-5 |

### Address Fields

| Fieldname | Fieldtype | Label | Descripción |
|-----------|-----------|-------|-------------|
| `sifen_numero_casa` | Data | Número de Casa | Número casa |

### Sales Invoice Fields

| Fieldname | Fieldtype | Label | Descripción |
|-----------|-----------|-------|-------------|
| `custom_numero_control` | Data | Número de Control | 9 dígitos único |
| `custom_einvoice_json` | Code | E-Invoice JSON | Payload enviado |
| `custom_einvoice_generated` | Check | E-Invoice Generated | Flag |
| `custom_einvoice_generated_date` | Datetime | E-Invoice Generated Date | Fecha generación |
| `custom_sifen_factura_id` | Data | SIFEN Factura ID | ID de SIFEN |
| `custom_sifen_correlativo` | Data | SIFEN Correlativo | Correlativo |
| `custom_sifen_estado` | Data | SIFEN Estado | Estado |
| `custom_sifen_cdc` | Data | SIFEN CDC | CDC |
| `custom_sifen_xml_link` | Data | SIFEN XML Link | URL XML |
| `custom_sifen_kude_link` | Data | SIFEN KUDE Link | URL KUDE |

---

## DocTypes Personalizados

### E-Invoice Actividad Economica

**Child Table** para actividades económicas de la empresa.

| Field | Fieldtype | Label | Reqd |
|-------|-----------|-------|------|
| `codigo_actividad` | Data | Código de Actividad | Yes |
| `descripcion_actividad` | Data | Descripción de Actividad | Yes |

---

## API Externa FEPY

### Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/facturar/crear` | Crear factura |
| GET | `/api/invoices/{id}` | Consultar estado |
| GET | `/api/invoices/{id}/download-xml` | Descargar XML |
| GET | `/api/invoices/{id}/download-pdf` | Descargar KUDE |

### Authentication

```
Authorization: Bearer {API_KEY}
```

### Request Format

```json
{
  "param": { ... },
  "data": { ... }
}
```

### Response Format

```json
{
  "success": true,
  "message": "...",
  "data": {
    "facturaId": "...",
    "correlativo": "...",
    "estado": "...",
    "cdc": "...",
    "xmlLink": "...",
    "kudeLink": "..."
  }
}
```

---

## Base de Datos

### Índices Personalizados

```sql
-- Índice único para número de control (performance)
ALTER TABLE `tabSales Invoice` 
ADD UNIQUE INDEX `idx_custom_numero_control` (`custom_numero_control`);
```

### Tablas Involucradas

| Tabla | Descripción |
|-------|-------------|
| `tabCompany` | Datos de empresa |
| `tabCustomer` | Datos de cliente |
| `tabAddress` | Direcciones |
| `tabSales Invoice` | Facturas |
| `tabSales Invoice Item` | Items de factura |
| `tabItem Tax Template` | Plantillas de impuesto |
| `tabItem Tax Template Detail` | Detalle de impuestos |
| `tabE-Invoice Actividad Economica` | Actividades económicas |
| `tabError Log` | Logs de errores |

---

## Permisos y Roles

### Roles Utilizados

| Rol | Descripción |
|-----|-------------|
| Administrator | Acceso completo, incluyendo Regenerate |
| Accounts Manager | Crear, validar, enviar a SIFEN |
| Accounts User | Crear, validar |
| Auditor | Solo lectura |

### Permisos por Botón

| Botón | Roles Visibles |
|-------|---------------|
| Generar E-Invoice | Todos |
| Regenerate and Send | Administrator |
| Download XML | Todos |
| Download KUDE | Todos |
| Check Local Status | Todos |
| Refresh Status | Todos |

---

## Constantes y Valores

### Tipos de Documento SIFEN

| Código | Descripción |
|--------|-------------|
| 1 | Factura electrónica |
| 5 | Nota de crédito electrónica |
| 6 | Nota de débito electrónica |

### Tipos de Operación

| Código | Descripción |
|--------|-------------|
| 1 | B2B |
| 2 | B2C |
| 3 | B2G |
| 4 | B2F |

### Tipos de Impuesto

| Código | Descripción |
|--------|-------------|
| 1 | IVA |
| 2 | ISC |
| 3 | Renta |
| 4 | Ninguno |
| 5 | IVA-Renta |

### Afectación al IVA

| Código | Descripción |
|--------|-------------|
| 1 | Gravado IVA |
| 2 | Exonerado |
| 3 | Exento |
| 4 | Parcial |

---

## Referencias

- [Frappe Framework Docs](https://frappeframework.com/docs)
- [Frappe Custom Field](https://frappeframework.com/docs/user/en/customization/custom-field)
- [Frappe Hooks](https://frappeframework.com/docs/user/en/tutorial/hooks)
- [SIFEN Official](https://www.set.gov.py/)
- [Manual Técnico SIFEN v150](../../Manual_Técnico_Versión_150.md)

---

**Última actualización:** 2026-03-28
