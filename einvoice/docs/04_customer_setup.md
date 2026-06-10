# Configuración del Customer

Este documento describe la configuración requerida en **Customer** para el módulo E-Invoice.

---

## Campos Obligatorios SIFEN

### 1. SIFEN Es contribuyente?

- **Fieldname**: `sifen_contribuyente`
- **Fieldtype**: Check
- **Sección**: Tax Information
- **Label**: "Es contribuyente?"
- **Descripción**: Indica si el cliente es contribuyente del sistema de facturación electrónica
- **Obligatorio**: ✅ Sí (para determinar tipoOperacion)

**Configuración:**
```
Customer → Tax Information → Es contribuyente? = ✓ (marcado)
```

**Uso:**
- `True` = Es contribuyente (tipoImpuesto = 1 para Paraguay)
- `False` = No contribuyente (tipoImpuesto = 4 para extranjeros sin RUC)

---

### 2. SIFEN Tipo Contribuyente

- **Fieldname**: `sifen_tipo_contribuyente`
- **Fieldtype**: Select
- **Sección**: Tax Information (después de sifen_contribuyente)
- **Label**: "SIFEN Tipo Contribuyente"
- **Descripción**: Tipo de contribuyente según SIFEN
- **Visibilidad**: Solo se muestra cuando **Es contribuyente? = ✓**
- **Opciones**:
  ```
  1|Persona Física
  2|Persona Jurídica
  ```
- **Obligatorio**: ✅ Sí (cuando es contribuyente)

**Configuración:**
```
Customer → Tax Information → SIFEN Tipo Contribuyente = "1|Persona Física"
```

---

### 3. SIFEN Tipo Documento

- **Fieldname**: `sifen_tipo_documento`
- **Fieldtype**: Select
- **Sección**: Tax Information (después de sifen_contribuyente)
- **Label**: "SIFEN Tipo Documento"
- **Descripción**: Tipo de documento del cliente según SIFEN
- **Visibilidad**: Solo se muestra cuando **Es contribuyente? = ☐ (desmarcado)**
- **Opciones**:
  ```
  1|RUC
  2|CI (Cédula de Identidad)
  3|Pasaporte
  4|Otro
  ```
- **Obligatorio**: ✅ Sí (cuando NO es contribuyente)

**Configuración:**
```
Customer → Tax Information → SIFEN Tipo Documento = "1|RUC"
```

**Valores según tipo de operación:**

| Operación | Tipo Documento | Código |
|-----------|---------------|--------|
| B2B | RUC | 1 |
| B2G | RUC | 1 |
| B2C | RUC o CI | 1 o 2 |
| Consumidor Final (Extranjero) | Pasaporte u Otro | 3 o 4 |

**Validaciones:**
- B2B/B2G: Debe ser "1" (RUC)
- B2C: Debe ser "1" (RUC) o "2" (CI)
- Consumidor Final (Extranjero): Debe ser "3" (Pasaporte) o "4" (Otro)

---

### 4. SIFEN Tipo Impuesto

- **Fieldname**: `sifen_tipo_impuesto`
- **Fieldtype**: Select
- **Sección**: Tax Information (después de sifen_tipo_documento)
- **Label**: "SIFEN Tipo Impuesto"
- **Descripción**: Tipo de impuesto según SIFEN D013
- **Opciones**:
  ```
  1|IVA (cliente local contribuyente)
  2|ISC (productos con impuesto selectivo)
  3|Renta (cliente extranjero con RUC)
  4|Ninguno (cliente extranjero sin RUC, consumidor final)
  5|IVA - Renta (mixto)
  ```
- **Obligatorio**: ✅ Sí

> **Nota:** Este campo establece el `tipoImpuesto` a nivel cabecera del payload.
> El `ivaTipo` a nivel de cada **item** se determina exclusivamente desde la
> **Item Tax Template** (campo `sifen_tipo_iva`). Ver [Configuración de Items](05_items_setup.md).

**Configuración:**
```
Customer → Tax Information → SIFEN Tipo Impuesto = "1|IVA (cliente local contribuyente)"
```

**Valores según tipo de operación:**

| Operación | Tipo Impuesto | Código | Descripción |
|-----------|--------------|--------|-------------|
| B2B (Paraguay) | IVA | 1 | Cliente local contribuyente |
| B2B (Paraguay) | ISC | 2 | Productos con impuesto selectivo |
| B2B (Paraguay) | IVA-Renta | 5 | Mixto |
| B2C (Paraguay) | IVA | 1 | Cliente local contribuyente |
| B2C (Paraguay) | ISC | 2 | Productos con impuesto selectivo |
| B2G (Paraguay) | IVA | 1 | Gobierno contribuyente |
| Extranjero (con RUC) | Renta | 3 | Cliente extranjero con RUC |
| Extranjero (sin RUC) | Ninguno | 4 | Consumidor final extranjero |

**Validaciones:**
- Paraguay (B2B/B2C/B2G): 1, 2, o 5 (NO 3 o 4)
- Extranjero: 3 o 4 (NO 1, 2, o 5)

---

## Configuración del Address del Customer

### 1. Número de Casa

- **Fieldname**: `sifen_numero_casa`
- **Fieldtype**: Data
- **Sección**: Address
- **Label**: "Número de Casa"
- **Descripción**: Número de casa según SIFEN
- **Obligatorio**: ❌ No (pero recomendado)

**Configuración:**
```
Address → Número de Casa = "123"
```

---

### 2. Departamento (State)

- **Fieldname**: `state`
- **Fieldtype**: Link (Country)
- **Sección**: Address
- **Label**: "State" (Departamento en Paraguay)
- **Descripción**: Departamento del Paraguay
- **Formato**: "12|CENTRAL" (código|descripción)
- **Obligatorio**: ✅ Sí (para Paraguay)

**Configuración:**
```
Address → State = "12|CENTRAL" (usar botón 🔍 Buscar Departamento)
```

**Departamentos de Paraguay:**
```
1|ASUNCION
4|CORDILLERA
5|GUAIRA
6|CAAGUAZU
7|CAAZAPA
8|ITAPUA
9|MISIONES
10|PARAGUARI
11|ALTO PARANA
12|CENTRAL
13|ALTO PARAGUAY
14|AMAMBAY
15|CANINDEYU
16|PRESIDENTE HAYES
17|NEEMBUCU
```

---

### 3. Distrito (County)

- **Fieldname**: `county`
- **Fieldtype**: Link (County)
- **Sección**: Address
- **Label**: "County" (Distrito en Paraguay)
- **Descripción**: Distrito del Paraguay
- **Formato**: "158|LIMPIO" (código|descripción)
- **Obligatorio**: ✅ Sí (para Paraguay)

**Configuración:**
```
Address → County = "158|LIMPIO" (usar botón 🔍 Buscar Distrito)
```

---

### 4. Ciudad (City)

- **Fieldname**: `city`
- **Fieldtype**: Data
- **Sección**: Address
- **Label**: "City"
- **Descripción**: Ciudad del Paraguay
- **Formato**: "5940|LIMPIO (MUNICIPIO)" (código|descripción)
- **Obligatorio**: ✅ Sí (para Paraguay)

**Configuración:**
```
Address → City = "5940|LIMPIO (MUNICIPIO)" (usar botón 🔍 Buscar Ciudad)
```

---

### 5. Teléfono

- **Fieldname**: `phone`
- **Fieldtype**: Data
- **Sección**: Address
- **Label**: "Phone"
- **Descripción**: Teléfono del cliente
- **Obligatorio**: ❌ No (pero recomendado)
- **Prioridad**: ✅ Se usa antes que Customer.mobile_no

**Configuración:**
```
Address → Phone = "+595 981 123456"
```

---

### 6. Email

- **Fieldname**: `email_id`
- **Fieldtype**: Data
- **Sección**: Address
- **Label**: "Email"
- **Descripción**: Email del cliente
- **Obligatorio**: ❌ No (pero recomendado)
- **Prioridad**: ✅ Se usa antes que Customer.email_id

**Configuración:**
```
Address → Email = "cliente@email.com"
```

---

## Configuración Paso a Paso

### Paso 1: Ir a Customer List

```
Menu → Selling → Customers → Customer List
```

### Paso 2: Seleccionar o Crear Customer

- Click en el cliente a configurar
- O crear uno nuevo

### Paso 3: Completar Tax Information

Desplazarse hasta la sección **Tax Information** y completar según el tipo de cliente:

**Si es contribuyente (B2B/B2G):**
```
1. Tax ID: 123456-1
2. Es contribuyente?: ✓ (marcado)
3. SIFEN Tipo Contribuyente: 1|Persona Física o 2|Persona Jurídica
4. SIFEN Tipo Impuesto: 1|IVA (cliente local contribuyente)
```

**Si NO es contribuyente (B2C):**
```
1. Tax ID: (Según tipo documento)
2. Es contribuyente?: ☐ (desmarcado)
3. SIFEN Tipo Documento: 1|CI (Cédula de Identidad) o 2|Pasaporte etc.
4. SIFEN Tipo Impuesto: 1|IVA (cliente local contribuyente)
```

### Paso 4: Configurar Address

1. Ir a **Address** del customer
2. Click en **Add Address** o editar existente
3. Completar:
   ```
   - Address Line 1: Av. Principal 123
   - Address Line 2: Edificio XYZ
   - Número de Casa: 123
   - State: 12|CENTRAL (usar 🔍 Buscar Departamento)
   - County: 158|LIMPIO (usar 🔍 Buscar Distrito)
   - City: 5940|LIMPIO (MUNICIPIO) (usar 🔍 Buscar Ciudad)
   - Phone: +595 981 123456
   - Email: cliente@email.com
   ```
4. Guardar

### Paso 5: Seleccionar Categoria del Ciente

El **Categoria del Ciente** es **obligatorio** y determina el tipo de operación.
No puede usarse "Todas las Categorias".

```
Menu → Selling → Customer Group

- Para B2B: "Comercial" o una categoría empresarial
- Para B2C: "Persona Física" o "Consumer"
- Para B2G: "Government" o "Gubernamental"
- Para B2F: "Sin fines de lucro" o "Foundation"
```

## Valores de tipoOperacion

| Código | Tipo | Descripción |
|--------|------|-------------|
| 1 | B2B | Venta entre empresas (ambos contribuyentes) |
| 2 | B2C | Consumidor final nacional o extranjero |
| 3 | B2G | Gobierno/Entidades públicas |
| 4 | B2F | **Fundaciones y Asociaciones sin fines de lucro** (SIFEN v150) |

---

## Ejemplos de Configuración

### Ejemplo 1: Customer B2B (Paraguay — Contribuyente)

```
Customer:
  - Customer Name: "Empresa S.A."
  - Customer Type: "Company"
  - Categoria del Cliente: "Comercial"
  - Tax ID: "123456-1"
  - sifen_contribuyente: ✓ (marcado)
  - sifen_tipo_contribuyente: "2|Persona Jurídica"
  - sifen_tipo_impuesto: "1|IVA (cliente local contribuyente)"

Address:
  - Country: "Paraguay"
  - State: "12|CENTRAL"
  - County: "158|LIMPIO"
  - City: "5940|LIMPIO (MUNICIPIO)"
  - Phone: "+595 981 123456"
  - Email: "contacto@empresa.com.py"

Resultado:
  - tipoOperacion: 1 (B2B)
  - tipoImpuesto: 1 (IVA)
```

### Ejemplo 2: Customer B2C (Consumidor Final — No Contribuyente)

```
Customer:
  - Customer Name: "Juan Pérez"
  - Customer Type: "Individual"
  - Categoria del Cliente: "Persona Física"
  - Tax ID: (Según tipo documento, CI, Pasaporte)
  - sifen_contribuyente: ☐ (desmarcado)
  - sifen_tipo_documento: "2|CI (Cédula de Identidad)"
  - sifen_tipo_impuesto: "1|IVA (cliente local contribuyente)"

Address:
  - Country: "Paraguay"
  - State: "1|ASUNCION"
  - County: "1|ASUNCION"
  - City: "1|ASUNCION"

Resultado:
  - tipoOperacion: 2 (B2C)
  - tipoImpuesto: 1 (cliente local contribuyente)
```

### Ejemplo 3: Customer Extranjero — No Contribuyente

```
Customer:
  - Customer Name: "John Doe"
  - Customer Type: "Individual"
  - Categoria del Cliente: "Persona Física"
  - Tax ID: (Según tipo documento)
  - sifen_contribuyente: ☐ (desmarcado)
  - sifen_tipo_documento: "3|Pasaporte"
  - sifen_tipo_impuesto: "4|Ninguno (cliente extranjero sin RUC, consumidor final)"

Address:
  - Country: "United States"
  - State: (vacío)
  - County: (vacío)
  - City: "New York"

Resultado:
  - tipoOperacion: 2 (B2C - Consumidor Final)
  - tipoImpuesto: 4 (Ninguno)
  - departamento/distrito/ciudad: null
```

### Ejemplo 4: Customer B2G (Gobierno — Contribuyente)

```
Customer:
  - Customer Name: "Ministerio de Hacienda"
  - Customer Type: "Company"
  - Categoria del Cliente: "Gubernamental"
  - Tax ID: "123456-1"
  - sifen_contribuyente: ✓ (marcado)
  - sifen_tipo_contribuyente: "2|Persona Jurídica"
  - sifen_tipo_impuesto: "1|IVA (cliente local contribuyente)"

Address:
  - Country: "Paraguay"
  - State: "1|ASUNCION"
  - County: "1|ASUNCION"
  - City: "1|ASUNCION"

Resultado:
  - tipoOperacion: 3 (B2G)
  - tipoImpuesto: 1 (IVA)
```

---

## Validaciones

### En Customer (al guardar el Customer)

| Campo | Validación | Error si falla |
|-------|-----------|----------------|
| sifen_contribuyente | ✓ + sifen_tipo_contribuyente requerido | "SIFEN Tipo Contribuyente es requerido para contribuyentes" |
| sifen_contribuyente | ✓ + tax_id requerido | "Tax ID es requerido para contribuyentes" |
| sifen_contribuyente | ☐ + sifen_tipo_documento requerido | "SIFEN Tipo Documento es requerido para no contribuyentes" |
| customer_group | No puede ser "Todas las Categorias" | "Categoria del Cliente no puede ser Todas las Categorias" |

### En Sales Invoice / POS Invoice (al guardar o validar)

| Campo | Validación | Error si falta |
|-------|-----------|----------------|
| sifen_tipo_documento | No vacío | "SIFEN Tipo Documento del cliente está vacío" |
| sifen_tipo_impuesto | No vacío | "SIFEN Tipo Impuesto del cliente está vacío" |
| sifen_tipo_transaccion | No vacío (en Sales Invoice / POS Invoice) | "SIFEN Tipo de Transacción es requerido" |
| sifen_tipo_documento (B2B/B2G) | = "1" | "Debe tener SIFEN Tipo Documento = 'RUC'" |
| sifen_tipo_documento (B2C) | = "1" o "2" | "Debe tener SIFEN Tipo Documento = 'RUC' o 'CI'" |
| sifen_tipo_documento (Extranjero) | = "3" o "4" | "Debe tener SIFEN Tipo Documento = 'Pasaporte' o 'Otro'" |
| sifen_tipo_impuesto (Paraguay) | 1, 2, o 5 | "No es coherente con el tipo de operación" |
| sifen_tipo_impuesto (Extranjero) | 3 o 4 | "No es coherente con el tipo de operación" |
| Address.state (Paraguay) | No vacío | "Departamento (State) es obligatorio" |
| Address.county (Paraguay) | No vacío | "Distrito (County) es obligatorio" |
| Address.city (Paraguay) | No vacío | "Ciudad (City) es obligatoria" |

---

## Errores Comunes

### 1. "SIFEN Tipo Documento del cliente está vacío"

**Causa**: No se configuró `sifen_tipo_documento`

**Solución**:
```
Customer → Tax Information → SIFEN Tipo Documento = "1|RUC"
```

### 2. "El cliente para operación B2B debe tener SIFEN Tipo Documento = 'RUC'"

**Causa**: El customer es B2B pero tiene tipo documento diferente a RUC

**Solución**:
```
Customer → Tax Information → SIFEN Tipo Documento = "1|RUC"
```

### 3. "El SIFEN Tipo Impuesto no es coherente con el tipo de operación"

**Causa**: El tipo de impuesto no coincide con el tipo de operación

**Solución**:
- Para Paraguay: Usar 1, 2, o 5
- Para Extranjero: Usar 3 o 4

### 4. "Departamento (State) es obligatorio en el address del cliente"

**Causa**: El address no tiene departamento configurado

**Solución**:
```
Address → State = usar botón 🔍 Buscar Departamento
```

---

## Referencias

- [Manual Técnico SIFEN v150](../../Manual_Técnico_Versión_150.md)
- [Campos SIFEN](02_sifen_fields.md)
- [Configuración de la Empresa](03_company_setup.md)
- [Validaciones](06_validations.md)

---

**Última actualización:** 2026-06-10
