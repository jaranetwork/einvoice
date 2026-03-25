# Configuración de Items e Item Tax Template

Este documento describe la configuración requerida en **Items** e **Item Tax Template** para el módulo E-Invoice.

---

## Item Tax Template

### Descripción General

El **Item Tax Template** es donde se configura la afectación al IVA según SIFEN. Cada item debe tener asociado un Item Tax Template con el campo `sifen_tipo_iva` configurado.

---

### Campos Obligatorios

#### 1. tax_rate (Tasa de Impuesto)

- **Fieldname**: `tax_rate`
- **Fieldtype**: Float
- **Child Table**: Item Tax Template Detail
- **Label**: "Tax Rate"
- **Descripción**: Tasa de impuesto en porcentaje
- **Obligatorio**: ✅ Sí
- **Valores comunes**:
  - `10.0` = IVA 10%
  - `5.0` = IVA 5%
  - `0.0` = Exento/Exonerado

**Configuración:**
```
Item Tax Template → Taxes → Tax Rate = 10.0
```

#### 2. sifen_tipo_iva (SIFEN Tipo IVA)

- **Fieldname**: `sifen_tipo_iva`
- **Fieldtype**: Select
- **Child Table**: Item Tax Template Detail
- **Label**: "SIFEN Tipo IVA"
- **Descripción**: Tipo de afectación al IVA según SIFEN D013
- **Opciones**:
  ```
  1|Gravado IVA
  2|Exonerado (Art.83- Ley 125/91)
  3|Exento (no IVA)
  4|Gravado parcial
  ```
- **Obligatorio**: ✅ Sí (al menos una línea debe tener configurado)

**Configuración:**
```
Item Tax Template → Taxes → SIFEN Tipo IVA = "1|Gravado IVA"
```

---

### Tipos de Afectación al IVA (sifen_tipo_iva)

#### 1 = Gravado IVA

- **Descripción**: Item con IVA completo
- **ivaProporcion**: 100%
- **iva (tasa)**: 10.0% (o la tasa configurada)
- **Uso**: Items estándar con IVA

**Ejemplo:**
```
Item Tax Template: "IVA 10%"
Taxes:
  - Tax Type: "VAT 10%"
  - Tax Rate: 10.0
  - SIFEN Tipo IVA: "1|Gravado IVA"
```

#### 2 = Exonerado (Art.83- Ley 125/91)

- **Descripción**: Item exonerado según Art.83 de Ley 125/91
- **ivaProporcion**: 0%
- **iva (tasa)**: 0.0%
- **Uso**: Items exonerados por ley específica

**Ejemplo:**
```
Item Tax Template: "Exonerado Art.83"
Taxes:
  - Tax Type: "Exonerado"
  - Tax Rate: 0.0
  - SIFEN Tipo IVA: "2|Exonerado (Art.83- Ley 125/91)"
```

#### 3 = Exento (no IVA)

- **Descripción**: Item exento de IVA
- **ivaProporcion**: 0%
- **iva (tasa)**: 0.0%
- **Uso**: Items que no llevan IVA

**Ejemplo:**
```
Item Tax Template: "Exento"
Taxes:
  - Tax Type: "Exento"
  - Tax Rate: 0.0
  - SIFEN Tipo IVA: "3|Exento (no IVA)"
```

#### 4 = Gravado parcial

- **Descripción**: Item con gravamen parcial de IVA
- **ivaProporcion**: Parcial (según corresponda)
- **iva (tasa)**: Variable
- **Uso**: Items con reducción de base imponible

**Ejemplo:**
```
Item Tax Template: "Gravado Parcial"
Taxes:
  - Tax Type: "VAT Parcial"
  - Tax Rate: 5.0
  - SIFEN Tipo IVA: "4|Gravado parcial"
```

---

## Configuración Paso a Paso

### Paso 1: Crear Item Tax Template

```
Menu → Accounting → Masters → Item Tax Template
```

1. Click en **Add Item Tax Template**
2. Completar:
   ```
   - Title: "IVA 10%"
   - Company: [Seleccionar empresa]
   ```

### Paso 2: Agregar Línea de Impuesto

En la tabla **Taxes**:

1. Click en **Add Row**
2. Completar:
   ```
   - Tax Type: [Seleccionar cuenta de impuesto, ej: "VAT 10%"]
   - Tax Rate: 10.0
   - SIFEN Tipo IVA: "1|Gravado IVA"
   ```
3. Guardar

### Paso 3: Asignar al Item

```
Menu → Stock → Items → Item
```

1. Seleccionar o crear item
2. En **Item Tax Template**, seleccionar la plantilla creada
3. Guardar

---

## Ejemplos de Configuración

### Ejemplo 1: Item con IVA 10% (Gravado)

**Item Tax Template:**
```
Title: "IVA 10%"
Company: "Tu Empresa S.A."

Taxes:
┌─────────────┬────────────┬──────────────────┐
│ Tax Type    │ Tax Rate   │ SIFEN Tipo IVA   │
├─────────────┼────────────┼──────────────────┤
│ VAT 10%     │ 10.0       │ 1|Gravado IVA    │
└─────────────┴────────────┴──────────────────┘
```

**Item:**
```
Item Code: "PRODUCTO-001"
Item Name: "Producto Ejemplo"
Item Tax Template: "IVA 10%"
```

**Resultado en SIFEN:**
```json
{
  "ivaTipo": 1,
  "ivaProporcion": 100,
  "iva": 10.0
}
```

---

### Ejemplo 2: Item Exento (no IVA)

**Item Tax Template:**
```
Title: "Exento"
Company: "Tu Empresa S.A."

Taxes:
┌─────────────┬────────────┬──────────────────┐
│ Tax Type    │ Tax Rate   │ SIFEN Tipo IVA   │
├─────────────┼────────────┼──────────────────┤
│ Exento      │ 0.0        │ 3|Exento         │
└─────────────┴────────────┴──────────────────┘
```

**Item:**
```
Item Code: "SERVICIO-001"
Item Name: "Servicio Exento"
Item Tax Template: "Exento"
```

**Resultado en SIFEN:**
```json
{
  "ivaTipo": 3,
  "ivaProporcion": 0,
  "iva": 0.0
}
```

---

### Ejemplo 3: Item Exonerado (Art.83)

**Item Tax Template:**
```
Title: "Exonerado Art.83"
Company: "Tu Empresa S.A."

Taxes:
┌─────────────┬────────────┬──────────────────────────────┐
│ Tax Type    │ Tax Rate   │ SIFEN Tipo IVA               │
├─────────────┼────────────┼──────────────────────────────┤
│ Exonerado   │ 0.0        │ 2|Exonerado (Art.83- Ley...) │
└─────────────┴────────────┴──────────────────────────────┘
```

**Item:**
```
Item Code: "MEDICAMENTO-001"
Item Name: "Medicamento Esencial"
Item Tax Template: "Exonerado Art.83"
```

**Resultado en SIFEN:**
```json
{
  "ivaTipo": 2,
  "ivaProporcion": 0,
  "iva": 0.0
}
```

---

### Ejemplo 4: Item con Gravamen Parcial

**Item Tax Template:**
```
Title: "Gravado Parcial 5%"
Company: "Tu Empresa S.A."

Taxes:
┌─────────────┬────────────┬──────────────────┐
│ Tax Type    │ Tax Rate   │ SIFEN Tipo IVA   │
├─────────────┼────────────┼──────────────────┤
│ VAT 5%      │ 5.0        │ 4|Gravado parcial│
└─────────────┴────────────┴──────────────────┘
```

**Item:**
```
Item Code: "PRODUCTO-002"
Item Name: "Producto con Reducción"
Item Tax Template: "Gravado Parcial 5%"
```

**Resultado en SIFEN:**
```json
{
  "ivaTipo": 4,
  "ivaProporcion": 100,
  "iva": 5.0
}
```

---

## Validaciones

Al guardar una Sales Invoice, el sistema valida:

| Validación | Descripción | Error si falla |
|-----------|-------------|----------------|
| Item Tax Template obligatorio | Cada item debe tener tax template | "El item #X no tiene Plantilla de Impuesto configurada" |
| Al menos una línea de impuesto | El template debe tener ≥1 línea | "La Plantilla de Impuesto no tiene líneas de impuesto" |
| sifen_tipo_iva configurado | Al menos una línea debe tener sifen_tipo_iva | "La Plantilla no tiene 'SIFEN Tipo IVA' configurado" |
| sifen_tipo_iva válido (1-4) | El valor debe ser 1, 2, 3, o 4 | "Valor inválido para SIFEN Tipo IVA" |
| tax_rate > 0% (Paraguay, gravado) | Items gravados deben tener tasa > 0 | "La Plantilla tiene todos los impuestos con tasa 0%" |

---

## Errores Comunes

### 1. "El item #1 no tiene Plantilla de Impuesto configurada"

**Causa**: El item no tiene Item Tax Template asignado

**Solución**:
```
Item → Item Tax Template = Seleccionar plantilla
```

### 2. "La Plantilla de Impuesto no tiene líneas de impuesto configuradas"

**Causa**: El Item Tax Template está vacío

**Solución**:
```
Item Tax Template → Taxes → Add Row
  - Tax Type: [Seleccionar]
  - Tax Rate: 10.0
  - SIFEN Tipo IVA: "1|Gravado IVA"
```

### 3. "La Plantilla de Impuesto no tiene el campo 'SIFEN Tipo IVA' configurado"

**Causa**: La línea de impuesto no tiene `sifen_tipo_iva`

**Solución**:
```
Item Tax Template → Taxes → SIFEN Tipo IVA = "1|Gravado IVA"
```

### 4. "La Plantilla de Impuesto tiene un valor inválido para SIFEN Tipo IVA"

**Causa**: El valor de `sifen_tipo_iva` no es 1-4

**Solución**:
```
Item Tax Template → Taxes → SIFEN Tipo IVA = 
  - "1|Gravado IVA" o
  - "2|Exonerado (Art.83- Ley 125/91)" o
  - "3|Exento (no IVA)" o
  - "4|Gravado parcial"
```

### 5. "La Plantilla de Impuesto tiene todos los impuestos con tasa 0%"

**Causa**: Para Paraguay, los items gravados deben tener tasa > 0%

**Solución**:
- Si el item es gravado: `Tax Rate = 10.0`
- Si el item es exento/exonerado: Verificar que `sifen_tipo_iva = 2 o 3`

---

## Mapeo a SIFEN

### Item Tax Template Detail → SIFEN items[]

| ERPNext Field | SIFEN Field | Ejemplo |
|--------------|-------------|---------|
| `tax_rate` | `items[].iva` | 10.0 |
| `sifen_tipo_iva` (código) | `items[].ivaTipo` | 1 |
| Determinado según ivaTipo | `items[].ivaProporcion` | 100 o 0 |

### Reglas de Mapeo

```python
# ivaTipo
if sifen_tipo_iva == "1|Gravado IVA":
    ivaTipo = 1
    ivaProporcion = 100
    iva = tax_rate  # 10.0

elif sifen_tipo_iva == "2|Exonerado":
    ivaTipo = 2
    ivaProporcion = 0
    iva = 0.0

elif sifen_tipo_iva == "3|Exento":
    ivaTipo = 3
    ivaProporcion = 0
    iva = 0.0

elif sifen_tipo_iva == "4|Gravado parcial":
    ivaTipo = 4
    ivaProporcion = 100  # o según corresponda
    iva = tax_rate  # 5.0
```

---

## Referencias

- [Manual Técnico SIFEN v150](../../Manual_Técnico_Versión_150.md)
- [Campos SIFEN](02_sifen_fields.md)
- [Validaciones](06_validations.md)

---

**Última actualización:** 2026-03-25
