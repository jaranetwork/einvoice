# Guía de Inicio Rápido

## Instalación

### 1. Instalar el módulo

```bash
cd /workspace/development/frappe-bench
bench install-app einvoice
bench clear-cache
```

### 2. Configurar E-Invoice Setting

1. Ir a **E-Invoice Setting** en el menú principal
2. Habilitar la opción **Enabled**
3. Configurar:
   - **API Endpoint**: URL de la API DTE-PY
   - **API Key**: Clave de autenticación DTE-PY
    - **Request Timeout**: Tiempo de espera (default: 30 segundos)
    - **Tipo de Emisión**: "1|Normal" (predeterminado)
      - `1|Normal`: Emisión estándar en línea contra SIFEN
      - `2|Contingencia`: Emisión offline (SIFEN con inconvenientes o sin internet)

### 3. Configurar Company

Ver [Configuración de la Empresa](03_company_setup.md) para detalles completos.

**Campos mínimos requeridos:**
- Tax ID (RUC)
- Código de Establecimiento (3 dígitos)
- Número de Timbrado
- Fecha de Timbrado
- Tipo de Contribuyente (1=Persona Física, 2=Persona Jurídica)
- Tipo de Régimen (1-8)
- Actividades Económicas (al menos una)
- Responsable SIFEN (tipo documento, número, nombre, cargo)

### 4. Configurar Customer

Ver [Configuración del Customer](04_customer_setup.md) para detalles completos.

**Campos mínimos requeridos:**
- sifen_tipo_documento (1=RUC, 2=CI, 3=Pasaporte, 4=Otro)
- sifen_tipo_impuesto (1=IVA, 2=ISC, 3=Renta, 4=Ninguno, 5=IVA-Renta)
- sifen_contribuyente (Check)

### 5. Configurar Address del Customer

**Campos mínimos requeridos:**
- Departamento (usar botón 🔍 Buscar Departamento)
- Distrito (usar botón 🔍 Buscar Distrito)
- Ciudad (usar botón 🔍 Buscar Ciudad)
- Número de Casa

### 6. Configurar Items

**Campos mínimos requeridos:**
- Item Tax Template con:
  - Al menos una línea de impuesto
  - sifen_tipo_iva configurado (1-4)
  - tax_rate > 0% (para items gravados)

---

## Primer Uso

### Crear Sales Invoice

1. Ir a **Sales Invoice List**
2. Click en **Add Sales Invoice**
3. Seleccionar Customer
4. Agregar Items
5. Verificar Payment Terms (si es crédito)
6. Guardar

### Validar Factura

1. Click en **Validate** (Submit)
2. El sistema ejecutará validaciones automáticas:
   - Campos requeridos de Company
   - Campos requeridos de Customer
   - Items con Item Tax Template
   - Payment Terms (si es crédito)
3. Si hay errores, se mostrarán en un mensaje
4. Si todo está correcto, la factura se valida

### Enviar a DTE-PY

1. Con la factura validada, ir al menú **E-Invoice**
2. Click en **Generar E-Invoice**
3. El sistema:
   - Extrae datos de la factura
   - Construye payload
   - Envía a API del sistema DTE-PY
   - Guarda respuesta en factura
4. Se muestra mensaje de éxito o error

### Descargar XML/KUDE

1. Después de enviar a DTE-PY, aparecen los botones:
   - **Download XML**: Descarga el XML de la factura
   - **Download KUDE**: Descarga el PDF (KUDE)
   - **Print PDF**: Abrir directamente la ventana para imprimir pdf (KUDE)
2. Los archivos se guardan en la carpeta de descargas del navegador
* Antes de descargar espere al menos 15 segundos hasta que el sistema DTE-PY complete las acciones.

---

## Flujo Básico

```
┌─────────────────┐
│ Crear Factura   │
│ (Draft)         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Guardar         │
│ (Validaciones)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Validar (Submit)│
│ (DocStatus = 1) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Send to DTE-PY   │
│ (API Call)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Descargar XML   │
│ Descargar KUDE  |
| Print PDF       │
└─────────────────┘
```

---

> ⚠️ **Contingencia**: Use "Tipo de Emisión = 2|Contingencia" en E-Invoice Setting
> cuando el sistema SIFEN esté con inconvenientes o no haya conexión a internet.
> Las facturas emitidas en contingencia se sincronizan cuando el servicio se restablece.

---

## Roles y Permisos

| Rol | Permisos |
|-----|----------|
| **Administrator** | Todos los permisos, incluyendo Regenerate and Send |
| **Accounts Manager** | Crear, validar, enviar a SIFEN |
| **Accounts User** | Crear, validar (no puede enviar a SIFEN) |
| **Auditor** | Solo lectura |

### Botón "Regenerate and Send"

- **Visible solo para**: Administrator
- **Propósito**: Regenerar y reenviar factura a SIFEN
- **Uso**: Cuando la factura se eliminó en DTE-PY o hay errores

---

## Próximos Pasos

1. [Campos SIFEN](02_sifen_fields.md) - Mapeo detallado de campos
2. [Configuración de la Empresa](03_company_setup.md) - Guía completa de Company
3. [Configuración del Customer](04_customer_setup.md) - Guía completa de Customer
4. [Validaciones](06_validations.md) - Todas las validaciones automáticas

---

**Última actualización:** 2026-03-25
