# Autofactura SIFEN

## ¿Qué es Autofactura?

Autofactura es un mecanismo SIFEN donde **el comprador emite la factura** en lugar del vendedor.

Se usa cuando el vendedor es un **productor agropecuario** o **pequeño contribuyente** que no emite facturas electrónicas. El comprador (empresa registrada) emite la factura de compra a nombre del productor y la envía a SIFEN.

> **Nota:** Esta es la **única** situación en que una Purchase Invoice se envía a SIFEN.
> Las compras a proveedores regulares o de transporte son solo para contabilidad interna
> y no requieren campos SIFEN ni envío a la SET.

### En ERPNext

| Aspecto | Detalle |
|---------|---------|
| **Doctype** | Purchase Invoice |
| **Supplier** | Configurado con campos de autofactura |
| **Tipo de Transacción** | `10` = Compra de productos, `11` = Compra de servicios |
| **Payload SIFEN** | Sección `autoFactura` dentro del XML |

---

## Requisitos

### 1. Supplier configurado para Autofactura

| Campo | Valor |
|-------|-------|
| `sifen_contribuyente` | ✅ Marcado |
| `sifen_tipo_impuesto` | `5|IVA - Renta (mixto). Requerido para Autofactura` |
| `sifen_autofactura` | ✅ Marcado |
| `sifen_tipo_autofactura` | `1|No contribuyente` o `2|Extranjero` |
| `sifen_tipo_constancias` | `1|Constancia de no ser contribuyente` o `2|Constancia de microproductores` |
| `supplier_constancia_numero` | Número de constancia SET |
| `supplier_constancia_control` | Control de constancia SET |

Ver [Configuración del Proveedor](06a_supplier_setup.md) para detalles completos.

### 2. Purchase Invoice

| Campo | Requerido |
|-------|-----------|
| Supplier | ✅ (autofactura configurado) |
| Items | ✅ (con Item Tax Template) |
| `sifen_tipo_transaccion` | ✅ No vacío |

**sifen_tipo_transaccion opciones para Autofactura:**
- `10` = Compra de productos
- `11` = Compra de servicios

---

## Proceso Paso a Paso

### 1. Crear Supplier

```
Supplier → Add Supplier
  Supplier Name: JUAN PEREZ
  Tax ID (RUC): 12345678-9
  SIFEN Es contribuyente?: ✓
  SIFEN Tipo Contribuyente: "1|Persona Física"
  SIFEN Tipo Documento: "1|Cédula paraguaya"
  SIFEN Tipo Impuesto: "5|IVA - Renta (mixto)"
  SIFEN Autofactura: ✓
  SIFEN Autofactura Tipo: "1|No contribuyente"
  SIFEN Autofactura Tipo de Constancias: "1|Constancia de no ser contribuyente"
  SIFEN Autofactura Constancia Número: 12345
  SIFEN Autofactura Constancia Control: 98765
```

### 2. Crear Purchase Invoice

```
Purchase Invoice → Add Purchase Invoice
  Supplier: JUAN PEREZ
  Items:
    - Item: Maíz (con Item Tax Template configurado)
    - Qty: 100
    - Rate: 5.000 Gs.
  Tipo de Transacción SIFEN: "10|Compra de productos"
  Guardar → Validar (Submit)
```

### 3. Enviar a SIFEN

1. Con la Purchase Invoice validada, ir al menú **E-Invoice**
2. Click en **Generar E-Invoice**
3. El sistema envía el payload con la sección `autoFactura`
4. Esperar la respuesta con el CDC

---

## Estructura del Payload

La sección `autoFactura` se incluye automáticamente cuando el documento es una **Purchase Invoice** con **proveedor autofactura**:

```json
{
  "autoFactura": {
    "tipoVendedor": 1,
    "documentoTipo": 1,
    "documentoNumero": "12345678-9",
    "nombre": "JUAN PEREZ",
    "direccion": "Ruta 2 Km 18",
    "numeroCasa": "0",
    "departamento": 1,
    "departamentoDescripcion": "CAPITAL",
    "distrito": 101,
    "distritoDescripcion": "ASUNCION",
    "ciudad": 1,
    "ciudadDescripcion": "ASUNCION",
    "ubicacion": {
      "lugar": "Ruta 2 Km 18",
      "departamento": 1,
      "departamentoDescripcion": "CAPITAL",
      "distrito": 101,
      "distritoDescripcion": "ASUNCION",
      "ciudad": 1,
      "ciudadDescripcion": "ASUNCION"
    }
  }
}
```

### Campos del Payload

| Campo SIFEN | Fuente ERPNext |
|-------------|----------------|
| `tipoVendedor` | `Supplier.sifen_tipo_autofactura` (1=No contribuyente, 2=Extranjero) |
| `documentoTipo` | `Supplier.sifen_tipo_documento` |
| `documentoNumero` | `Supplier.tax_id` (RUC) |
| `nombre` | `Supplier.supplier_name` |
| `direccion` | `Address.address_line1` del Supplier |
| `numeroCasa` | `Address.sifen_numero_casa` del Supplier |
| `departamento` / `distrito` / `ciudad` | `Address.state` / `Address.county` / `Address.city` del Supplier |
| `ubicacion.*` | Misma dirección (ubicación de la transacción) |

---

## Validaciones

### Al guardar el Supplier

Ver [Configuración del Proveedor](06a_supplier_setup.md#validaciones).

### Al validar la Purchase Invoice

Las validaciones estándar de `validar_campos_sifen()` se aplican a Purchase Invoice:

- Company: RUC, establecimiento, timbrado, actividades
- Customer (suplanta al Supplier): tipo_documento, tipo_impuesto
- Items: Item Tax Template, sifen_tipo_iva
- Sales Taxes and Charges

No se requiere `sifen_tipo_transaccion` en `before_submit` (esa validación solo aplica a Sales Invoice y POS Invoice).

---

## Ejemplo Completo

### Supplier

```
Supplier Name: MARIA GONZALEZ
Tax ID (RUC): 87654321-0
sifen_contribuyente: ✓
sifen_tipo_contribuyente: "1|Persona Física"
sifen_tipo_documento: "1|Cédula paraguaya"
sifen_tipo_impuesto: "5|IVA - Renta (mixto)"
sifen_autofactura: ✓
sifen_tipo_autofactura: "1|No contribuyente"
sifen_tipo_constancias: "2|Constancia de microproductores"
supplier_constancia_numero: 67890
supplier_constancia_control: 54321
```

### Purchase Invoice

```
Purchase Invoice: COMP-PROD-2026-00001
Supplier: MARIA GONZALEZ
Items:
  - Soja, 50 kg, 8.000 Gs./kg → Total 400.000 Gs.
  - Sésamo, 30 kg, 12.000 Gs./kg → Total 360.000 Gs.
sifen_tipo_transaccion: "10|Compra de productos"
Total: 760.000 Gs.
IVA 5% (ivaTipo=1 sobre base gravada): 38.000 Gs.
```

---

## Referencias

- [Configuración del Proveedor](06a_supplier_setup.md)
- [Campos SIFEN](02_sifen_fields.md)
- [Validaciones](06_validations.md)
- [Manual Técnico SIFEN v150](../../Manual_Técnico_Versión_150.md)

---

**Última actualización:** 2026-06-10
