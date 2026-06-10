# Configuración del Proveedor (Supplier)

## ¿Para qué se usa el Supplier en SIFEN?

El Supplier en ERPNext se usa para **gestión de compras y contabilidad**. En el contexto SIFEN, hay tres escenarios:

| Tipo de Supplier | ¿Se envía a SIFEN? | ¿Dónde se usa? |
|-----------------|-------------------|----------------|
| Proveedor normal (compras) | ❌ No | Contabilidad interna |
| Proveedor transportista | ✅ Sí (datos del transportista) | Delivery Note / Nota de Remisión |
| Proveedor para Autofactura | ✅ Sí (factura completa) | Purchase Invoice |

### Proveedor normal
Para compras regulares o servicios. **No requiere** campos SIFEN — solo se usa para contabilidad interna.

### Proveedor transportista
Cuando el proveedor actúa como transportista en una Nota de Remisión (Delivery Note). El campo `transporter` en la Delivery Note vincula al Supplier, y sus datos SIFEN se incluyen en la sección `transporte.transportista` del payload.

**Campos requeridos para transportista:**
| Campo | Obligatorio | Uso en payload |
|-------|------------|----------------|
| `sifen_contribuyente` | ✅ Sí | Determina si se envía `ruc` o `documentoTipo`+`documentoNumero` |
| `tax_id` (RUC) | Según contribuyente | `ruc` (si contribuyente) o `documentoNumero` (si no) |
| `sifen_tipo_documento` | ✅ Si no es contribuyente | `documentoTipo` |
| Dirección principal | ✅ Sí | `direccion` del transportista |

Además, la Delivery Note puede incluir un **Chofer** (Driver) con licencia como `documentoNumero`.

### Proveedor para Autofactura
Requiere todos los campos SIFEN. Ver [Autofactura](06b_autofactura.md) para detalles.

---

---

## Campos SIFEN del Proveedor

### Orden en el Formulario

| # | Campo | Tipo | ¿Dónde aparece? | Descripción |
|---|-------|------|-----------------|-------------|
| 1 | `sifen_codigo_proveedor` | Data (auto) | Después de Supplier Name | Código único SUPP-YYYY-##### (se genera solo) |
| 2 | `sifen_contribuyente` | Check | Después de Tax ID | ¿Es contribuyente del sistema de facturación? |
| 3 | `sifen_tipo_contribuyente` | Select | Después de contribuyente | 1=Persona Física, 2=Persona Jurídica |
| 4 | `sifen_tipo_documento` | Select | Después de tipo contribuyente | Ver tabla abajo |
| 5 | `sifen_tipo_impuesto` | Select | Después de tipo documento | Ver tabla abajo |
| 6 | `sifen_autofactura` | Check | Después de tipo impuesto | Marcar si es proveedor de autofactura |
| 7 | `sifen_tipo_autofactura` | Select | Después de autofactura | Solo visible si autofactura ✓ |
| 8 | `sifen_tipo_constancias` | Select | Después de tipo autofactura | Solo visible si autofactura ✓ |
| 9 | `supplier_constancia_numero` | Data | Después de tipo constancias | Solo visible si autofactura ✓ |
| 10 | `supplier_constancia_control` | Data | Después de constancia número | Solo visible si autofactura ✓ |

### Detalle de Campos

#### sifen_codigo_proveedor

| Propiedad | Valor |
|-----------|-------|
| **Formato** | `SUPP-YYYY-#####` (ej: `SUPP-2026-00001`) |
| **Generación** | Automática al crear el Supplier |
| **Actualización** | `bench execute einvoice.e_invoice.doctype.supplier.supplier.update_existing_suppliers` |

#### sifen_tipo_documento

| Código | Descripción | ¿Cuándo usar? |
|--------|-------------|---------------|
| 1 | Cédula paraguaya | Proveedor local persona física |
| 2 | Pasaporte | Proveedor extranjero |
| 3 | Cédula extranjera | Proveedor extranjero con cédula |
| 4 | Carnet de residencia | Extranjero residente en PY |
| 5 | Innominado | Documento genérico |
| 6 | Tarjeta Diplomática | Exoneración fiscal |
| 9 | No especificado | No aplica |

#### sifen_tipo_impuesto

| Código | Descripción | Uso |
|--------|-------------|-----|
| 1 | IVA | Proveedor local contribuyente |
| 2 | ISC | Productos con impuesto selectivo |
| 3 | Renta | Proveedor extranjero con RUC |
| 4 | Ninguno | Proveedor extranjero sin RUC |
| 5 | IVA - Renta (mixto) | **Requerido para Autofactura** |

#### sifen_autofactura y subcampos

Ver [Autofactura](06b_autofactura.md) para detalles completos.

---

## Validaciones

Se ejecutan al guardar el Supplier:

| Caso | Validación | Error si falta |
|------|-----------|----------------|
| Autofactura ✓ | sifen_contribuyente debe estar marcado | "SIFEN Es contribuyente debe estar marcado" |
| Autofactura ✓ | sifen_tipo_contribuyente | "SIFEN Tipo Contribuyente" |
| Autofactura ✓ | sifen_tipo_documento | "SIFEN Tipo Documento" |
| Autofactura ✓ | sifen_tipo_impuesto | "SIFEN Tipo Impuesto" |
| Autofactura ✓ | sifen_tipo_autofactura | "SIFEN Autofactura Tipo" |
| Autofactura ✓ | sifen_tipo_constancias | "SIFEN Autofactura Tipo de Constancias" |
| Autofactura ✓ | supplier_constancia_numero | "SIFEN Autofactura Constancia Número" |
| Autofactura ✓ | supplier_constancia_control | "SIFEN Autofactura Constancia Control" |
| No autofactura + No contribuyente | sifen_tipo_documento | "SIFEN Tipo Documento" |
| No autofactura + No contribuyente | sifen_tipo_impuesto | "SIFEN Tipo Impuesto" |
| No autofactura + Contribuyente ✓ | sifen_tipo_contribuyente | "SIFEN Tipo Contribuyente" |
| No autofactura + Contribuyente ✓ | sifen_tipo_impuesto | "SIFEN Tipo Impuesto" |

---

## Pasos para Configurar

### Proveedor Normal (solo contabilidad, no va a SIFEN)

1. Ir a **Supplier List** → **Add Supplier**
2. Completar datos generales (Supplier Name, Tax ID si aplica)
3. Los campos SIFEN **no son necesarios**
4. Guardar

### Proveedor Transportista (para Delivery Note / Nota de Remisión)

1. Ir a **Supplier List** → **Add Supplier**
2. Completar datos generales (Supplier Name, RUT)
3. Configurar dirección principal del proveedor
4. En **Tax Information**:
   - Marcar **SIFEN Es contribuyente?** según corresponda
   - Si **no** es contribuyente: seleccionar **SIFEN Tipo Documento**
   - Si **sí** es contribuyente: completar **Tax ID (RUC)**
5. Guardar
6. En la **Delivery Note**, seleccionar este proveedor en el campo **Transporter**
7. Opcional: asignar un **Driver** (Chofer) con número de licencia

### Proveedor para Autofactura (vía Purchase Invoice a SIFEN)

1. Ir a **Supplier List** → **Add Supplier**
2. Completar datos generales (Supplier Name, Tax ID)
3. En **Tax Information**:
   - Marcar **SIFEN Es contribuyente?** ✅
   - Seleccionar **SIFEN Tipo Contribuyente**
   - Seleccionar **SIFEN Tipo Documento** (normalmente "1|Cédula paraguaya")
   - Seleccionar **SIFEN Tipo Impuesto** → **"5|IVA - Renta (mixto)"**
   - Marcar **SIFEN Autofactura** ✅
   - Seleccionar **SIFEN Autofactura Tipo** (1=No contribuyente, 2=Extranjero)
   - Seleccionar **SIFEN Autofactura Tipo de Constancias**
   - Completar **SIFEN Autofactura Constancia Número**
   - Completar **SIFEN Autofactura Constancia Control**
4. Guardar

---

## Ejemplos

### Ejemplo 1: Proveedor Normal (solo contabilidad)

```
Supplier Name: PAPELERA S.A.
Tax ID (RUC): 80012345-6
SIFEN Es contribuyente?: ☐ (no es necesario configurar)
```

### Ejemplo 2: Proveedor Transportista

```
Supplier Name: TRANSPORTE RAPIDO S.R.L.
Tax ID (RUC): 80098765-4
SIFEN Es contribuyente?: ✓
SIFEN Tipo Contribuyente: "2|Persona Jurídica"
Dirección principal: Av. Mariscal López 1234

Uso en Delivery Note:
  Transporter: TRANSPORTE RAPIDO S.R.L.
  Driver: PEDRO RAMIREZ (Licencia: 1234567)
```

### Ejemplo 3: Proveedor para Autofactura (Productor Agropecuario)

```
Supplier Name: JUAN PEREZ
Tax ID (RUC): 12345678-9
SIFEN Es contribuyente?: ✓
SIFEN Tipo Contribuyente: "1|Persona Física"
SIFEN Tipo Documento: "1|Cédula paraguaya"
SIFEN Tipo Impuesto: "5|IVA - Renta (mixto). Requerido para Autofactura"
SIFEN Autofactura: ✓
SIFEN Autofactura Tipo: "1|No contribuyente"
SIFEN Autofactura Tipo de Constancias: "1|Constancia de no ser contribuyente"
SIFEN Autofactura Constancia Número: 12345
SIFEN Autofactura Constancia Control: 98765
```

---

## Referencias

- [Autofactura](06b_autofactura.md)
- [Campos SIFEN](02_sifen_fields.md)
- [Validaciones](06_validations.md)
- [Manual Técnico SIFEN v150](../../Manual_Técnico_Versión_150.md)

---

**Última actualización:** 2026-06-10
