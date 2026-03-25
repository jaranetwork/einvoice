# Configuración de la Empresa

Este documento describe la configuración requerida en **Company** para el módulo E-Invoice.

---

## Campos Obligatorios

### 1. Tax ID (RUC)

- **Fieldname**: `tax_id`
- **Fieldtype**: Data
- **Sección**: Tax Information
- **Descripción**: RUC de la empresa según SET
- **Formato**: "123456-1" o "123456"
- **Obligatorio**: ✅ Sí

**Configuración:**
```
Company → Tax ID = "123456-1"
```

---

### 2. Código de Establecimiento

- **Fieldname**: `codigo_establecimiento`
- **Fieldtype**: Data
- **Sección**: SIFEN Campos Obligatorios
- **Descripción**: Código del establecimiento (HQ o sucursal)
- **Formato**: 3 dígitos (ej: "001", "002")
- **Obligatorio**: ✅ Sí
- **Validación**: Máximo 3 dígitos

**Configuración:**
```
Company → Codigo Establecimiento = "001"
```

---

### 3. Número de Timbrado

- **Fieldname**: `numero_timbrado`
- **Fieldtype**: Data
- **Sección**: SIFEN Campos Obligatorios
- **Descripción**: Número de timbrado otorgado por SET
- **Formato**: String (ej: "123456789")
- **Obligatorio**: ✅ Sí

**Configuración:**
```
Company → Numero Timbrado = "123456789"
```

---

### 4. Fecha de Timbrado

- **Fieldname**: `fecha_timbrado`
- **Fieldtype**: Date
- **Sección**: SIFEN Campos Obligatorios
- **Descripción**: Fecha de otorgamiento del timbrado
- **Formato**: YYYY-MM-DD
- **Obligatorio**: ✅ Sí

**Configuración:**
```
Company → Fecha Timbrado = "2024-01-01"
```

---

### 5. Tipo de Contribuyente

- **Fieldname**: `tipo_contribuyente`
- **Fieldtype**: Select
- **Sección**: SIFEN Campos Obligatorios
- **Descripción**: Tipo de contribuyente de la empresa
- **Opciones**:
  - `1` = Persona Física
  - `2` = Persona Jurídica
- **Obligatorio**: ✅ Sí

**Configuración:**
```
Company → Tipo Contribuyente = "2" (Persona Jurídica)
```

---

### 6. Tipo de Régimen

- **Fieldname**: `tipo_regimen`
- **Fieldtype**: Select
- **Sección**: SIFEN Campos Obligatorios
- **Descripción**: Tipo de régimen tributario
- **Opciones**:
  - `1` = Turismo
  - `2` = Importador
  - `3` = Exportador
  - `4` = Maquila
  - `5` = Ley 60/90
  - `6` = Pequeño Productor
  - `7` = Mediano Productor
  - `8` = Régimen Contable
- **Obligatorio**: ✅ Sí

**Configuración:**
```
Company → Tipo Regimen = "8" (Régimen Contable)
```

---

### 7. Denominación del Establecimiento

- **Fieldname**: `sifen_denominacion`
- **Fieldtype**: Data
- **Sección**: SIFEN Campos Obligatorios
- **Descripción**: Nombre o denominación del establecimiento
- **Obligatorio**: ❌ No (pero recomendado)

**Configuración:**
```
Company → Sifen Denominacion = "Casa Central"
```

---

### 8. Actividades Económicas (Child Table)

- **Fieldname**: `actividades_economicas`
- **Fieldtype**: Table
- **Child Table**: E-Invoice Actividad Economica
- **Sección**: SIFEN Campos Obligatorios
- **Descripción**: Lista de actividades económicas de la empresa
- **Obligatorio**: ✅ Sí (al menos una)

**Campos del Child Table:**

| Field | Fieldtype | Obligatorio | Descripción |
|-------|-----------|-------------|-------------|
| `codigo_actividad` | Data | ✅ Sí | Código de actividad SIFEN |
| `descripcion_actividad` | Data | ✅ Sí | Descripción de la actividad |

**Configuración:**
```
Company → Actividades Económicas → Agregar fila:
  - Código de Actividad: "01110"
  - Descripción de Actividad: "Cultivo de cereales"
```

**Ejemplo de actividades comunes:**
```
01110 - Cultivo de cereales
01120 - Cultivo de hortalizas
47111 - Comercio al por menor en supermercados
47911 - Comercio al por mayor por internet
62010 - Desarrollo de software
```

---

### 9. Responsable SIFEN (Firma Electrónica)

**Sección**: SIFEN Responsable

#### 9.1 Tipo de Documento

- **Fieldname**: `sifen_responsable_tipo_documento`
- **Fieldtype**: Select
- **Opciones**:
  - `1` = RUC
  - `2` = CI
  - `3` = Pasaporte
  - `4` = Otro
- **Obligatorio**: ✅ Sí

#### 9.2 Número de Documento

- **Fieldname**: `sifen_respons_numero_documento`
- **Fieldtype**: Data
- **Obligatorio**: ✅ Sí

#### 9.3 Nombre Completo

- **Fieldname**: `sifen_responsable_nombre`
- **Fieldtype**: Data
- **Obligatorio**: ✅ Sí

#### 9.4 Cargo

- **Fieldname**: `sifen_responsable_cargo`
- **Fieldtype**: Data
- **Obligatorio**: ✅ Sí

**Configuración completa:**
```
Company → SIFEN Responsable:
  - Tipo de Documento: "1" (RUC)
  - Número de Documento: "123456-1"
  - Nombre: "Juan Pérez"
  - Cargo: "Gerente General"
```

---

### 10. Punto de Expedición por Defecto

- **Fieldname**: `codigo_punto_expedicion_default`
- **Fieldtype**: Data
- **Sección**: SIFEN Campos Obligatorios
- **Descripción**: Código de punto de expedición por defecto
- **Formato**: 3 dígitos (ej: "001")
- **Obligatorio**: ❌ No (pero recomendado)

**Configuración:**
```
Company → Codigo Punto Expedicion Default = "001"
```

---

## Configuración Paso a Paso

### Paso 1: Ir a Company List

```
Menu → Accounting → Masters → Company
```

### Paso 2: Seleccionar o Crear Company

- Click en la empresa a configurar
- O crear una nueva

### Paso 3: Completar Tax Information

```
Tax ID: 123456-1
```

### Paso 4: Completar SIFEN Campos Obligatorios

Desplazarse hasta la sección **"SIFEN Campos Obligatorios"** y completar:

```
- Código de Establecimiento: 001
- Número de Timbrado: 123456789
- Fecha de Timbrado: 2024-01-01
- Tipo de Contribuyente: 2 (Persona Jurídica)
- Tipo de Régimen: 8 (Régimen Contable)
- Código Punto Expedición Default: 001
```

### Paso 5: Agregar Actividades Económicas

En la tabla **Actividades Económicas**:

1. Click en **Add Row**
2. Completar:
   - Código de Actividad: "01110"
   - Descripción de Actividad: "Cultivo de cereales"
3. Repetir para cada actividad

### Paso 6: Completar Responsable SIFEN

En la sección **SIFEN Responsable**:

```
- Tipo de Documento: 1 (RUC)
- Número de Documento: 123456-1
- Nombre: Juan Pérez
- Cargo: Gerente General
```

### Paso 7: Guardar

Click en **Save**

---

## Validaciones

Al guardar una Sales Invoice, el sistema valida:

| Campo | Validación | Error si falta |
|-------|-----------|----------------|
| Tax ID | No vacío | "Company Tax ID (RUC) is missing" |
| Codigo Establecimiento | No vacío, ≤3 dígitos | "Establishment Code is missing" |
| Numero Timbrado | No vacío | "Timbrado Number is missing" |
| Fecha Timbrado | No vacío | "Timbrado Date is missing" |
| Tipo Contribuyente | 1 o 2 | "Contributor Type is missing" |
| Tipo Regimen | 1-8 | "Tax Regimen is missing" |
| Actividades Económicas | ≥1 fila | "Economic Activities are missing" |
| Responsable (todos) | No vacío | "Responsible Person X is missing" |

---

## Errores Comunes

### 1. "Establishment Code cannot exceed 3 digits"

**Causa**: Se ingresó un código de más de 3 dígitos

**Solución**:
```
Incorrecto: "0001"
Correcto: "001"
```

### 2. "Economic Activity #1 is missing code"

**Causa**: La fila de actividad económica no tiene código

**Solución**: Completar el campo "Código de Actividad" en cada fila

### 3. "Responsible Person Document Type is missing"

**Causa**: No se configuró el responsable SIFEN

**Solución**: Completar los 4 campos del Responsable SIFEN

---

## Referencias

- [Manual Técnico SIFEN v150](../../Manual_Técnico_Versión_150.md)
- [Campos SIFEN](02_sifen_fields.md)
- [Configuración del Customer](04_customer_setup.md)

---

**Última actualización:** 2026-03-25
