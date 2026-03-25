# Configuración del Customer

Este documento describe la configuración requerida en **Customer** para el módulo E-Invoice.

---

## Campos Obligatorios SIFEN

### 1. sifen_contribuyente

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

### 2. sifen_tipo_documento

- **Fieldname**: `sifen_tipo_documento`
- **Fieldtype**: Select
- **Sección**: Tax Information (después de sifen_contribuyente)
- **Label**: "SIFEN Tipo Documento"
- **Descripción**: Tipo de documento del cliente según SIFEN
- **Opciones**:
  ```
  1|RUC
  2|CI (Cédula de Identidad)
  3|Pasaporte
  4|Otro
  ```
- **Obligatorio**: ✅ Sí

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
| B2F | Pasaporte u Otro | 3 o 4 |

**Validaciones:**
- B2B/B2G: Debe ser "1" (RUC)
- B2C: Debe ser "1" (RUC) o "2" (CI)
- B2F: Debe ser "3" (Pasaporte) o "4" (Otro)

---

### 3. sifen_tipo_impuesto

- **Fieldname**: `sifen_tipo_impuesto`
- **Fieldtype**: Select
- **Sección**: Tax Information (después de sifen_tipo_documento)
- **Label**: "SIFEN Tipo Impuesto"
- **Descripción**: Tipo de impuesto según SIFEN D013
- **Opciones**:
  ```
  1|IVA (cliente local contribuyente)
  2|ISC (productos con impuesto selectivo)
  3|Renta (cliente extranjero B2F con RUC)
  4|Ninguno (cliente extranjero sin RUC, consumidor final)
  5|IVA - Renta (mixto)
  ```
- **Obligatorio**: ✅ Sí

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
| B2F (Extranjero) | Renta | 3 | Extranjero con RUC |
| B2F (Extranjero) | Ninguno | 4 | Extranjero sin RUC |

**Validaciones:**
- Paraguay (B2B/B2C/B2G): 1, 2, o 5 (NO 3 o 4)
- Extranjero (B2F): 3 o 4 (NO 1, 2, o 5)

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

Desplazarse hasta la sección **Tax Information**:

```
1. Tax ID: 123456-1 (para B2B/B2G)
2. Es contribuyente?: ✓ (marcar si es contribuyente)
3. SIFEN Tipo Documento: 1|RUC
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

### Paso 5: Verificar Customer Group

El **Customer Group** determina el tipo de operación:

```
Menu → Selling → Customer Group

- Para B2B: "Company" o similar
- Para B2C: "Individual" o "Consumer"
- Para B2G: "Government" o "Gubernamental"
```

---

## Tipos de Operación (Determinación Automática)

El sistema determina automáticamente el `tipoOperacion` basado en:

### 1. País del Address

```
Si country ≠ "Paraguay" → tipoOperacion = 4 (B2F)
```

### 2. Customer Type

```
Si customer_type = "Company":
  Si customer_group contiene "gubernamental" → tipoOperacion = 3 (B2G)
  Si no → tipoOperacion = 1 (B2B)

Si customer_type = "Individual":
  Si country = "Paraguay" → tipoOperacion = 2 (B2C)
  Si country ≠ "Paraguay" → tipoOperacion = 4 (B2F)
```

### 3. Tax ID (RUC)

```
Si no tiene tax_id:
  Si country ≠ "Paraguay" → tipoOperacion = 4 (B2F)
  Si no → tipoOperacion = 2 (B2C)
```

---

## Ejemplos de Configuración

### Ejemplo 1: Customer B2B (Paraguay)

```
Customer:
  - Customer Name: "Empresa S.A."
  - Customer Type: "Company"
  - Customer Group: "Company"
  - Tax ID: "123456-1"
  - sifen_contribuyente: ✓ (marcado)
  - sifen_tipo_documento: "1|RUC"
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

### Ejemplo 2: Customer B2C (Consumidor Final)

```
Customer:
  - Customer Name: "Juan Pérez"
  - Customer Type: "Individual"
  - Customer Group: "Individual"
  - Tax ID: (vacío)
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
  - tipoImpuesto: 4 (Ninguno, por no tener RUC)
```

### Ejemplo 3: Customer B2F (Extranjero)

```
Customer:
  - Customer Name: "John Doe"
  - Customer Type: "Individual"
  - Customer Group: "Individual"
  - Tax ID: (vacío o RUC extranjero)
  - sifen_contribuyente: ☐ (desmarcado)
  - sifen_tipo_documento: "3|Pasaporte"
  - sifen_tipo_impuesto: "4|Ninguno (cliente extranjero sin RUC, consumidor final)"

Address:
  - Country: "United States"
  - State: (vacío)
  - County: (vacío)
  - City: "New York"

Resultado:
  - tipoOperacion: 4 (B2F)
  - tipoImpuesto: 4 (Ninguno)
  - departamento/distrito/ciudad: null
```

### Ejemplo 4: Customer B2G (Gobierno)

```
Customer:
  - Customer Name: "Ministerio de Hacienda"
  - Customer Type: "Company"
  - Customer Group: "Government" o "Gubernamental"
  - Tax ID: "123456-1"
  - sifen_contribuyente: ✓ (marcado)
  - sifen_tipo_documento: "1|RUC"
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

Al guardar una Sales Invoice, el sistema valida:

| Campo | Validación | Error si falta |
|-------|-----------|----------------|
| sifen_tipo_documento | No vacío | "SIFEN Tipo Documento del cliente está vacío" |
| sifen_tipo_impuesto | No vacío | "SIFEN Tipo Impuesto del cliente está vacío" |
| sifen_tipo_documento (B2B/B2G) | = "1" | "Debe tener SIFEN Tipo Documento = 'RUC'" |
| sifen_tipo_documento (B2C) | = "1" o "2" | "Debe tener SIFEN Tipo Documento = 'RUC' o 'CI'" |
| sifen_tipo_documento (B2F) | = "3" o "4" | "Debe tener SIFEN Tipo Documento = 'Pasaporte' o 'Otro'" |
| sifen_tipo_impuesto (Paraguay) | 1, 2, o 5 | "No es coherente con el tipo de operación" |
| sifen_tipo_impuesto (B2F) | 3 o 4 | "No es coherente con el tipo de operación" |
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

**Última actualización:** 2026-03-25
