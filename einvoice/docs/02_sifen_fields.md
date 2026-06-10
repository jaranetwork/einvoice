# Campos SIFEN - Mapeo ERPNext → SIFEN

Este documento describe el mapeo de campos entre ERPNext y el payload SIFEN.

---

## Estructura del Payload SIFEN

```json
{
  "param": { ... },      // Datos de la empresa
  "data": {              // Datos de la factura
    "cliente": { ... },  // Datos del cliente
    "usuario": { ... },  // Datos del usuario
    "factura": { ... },  // Datos de la factura
    "condicion": { ... },// Condición de pago
    "items": [ ... ],    // Items de la factura
    "totalPago": 0       // Total a pagar
  }
}
```

---

## Sección PARAM (Empresa)

### param.ruc
- **ERPNext**: `Company.tax_id`
- **SIFEN**: RUC de la empresa
- **Formato**: String (ej: "3604076-1")
- **Obligatorio**: ✅ Sí

### param.razonSocial
- **ERPNext**: `Company.name`
- **SIFEN**: Razón social de la empresa
- **Obligatorio**: ✅ Sí

### param.nombreFantasia
- **ERPNext**: `Company.name` (mismo que razón social)
- **SIFEN**: Nombre de fantasía
- **Obligatorio**: ✅ Sí

### param.actividadesEconomicas[]
- **ERPNext**: `Company.actividades_economicas[]` (Child Table)
- **SIFEN**: Array de actividades económicas
- **Estructura**:
  ```json
  {
    "codigo": "01110",      // Código de actividad
    "descripcion": "..."    // Descripción
  }
  ```
- **Obligatorio**: ✅ Sí (al menos una)

### param.timbradoNumero
- **ERPNext**: `Company.numero_timbrado`
- **SIFEN**: Número de timbrado
- **Formato**: String (ej: "123456789")
- **Obligatorio**: ✅ Sí

### param.timbradoFecha
- **ERPNext**: `Company.fecha_timbrado`
- **SIFEN**: Fecha de timbrado
- **Formato**: Date (YYYY-MM-DD)
- **Obligatorio**: ✅ Sí

### param.tipoContribuyente
- **ERPNext**: `Company.tipo_contribuyente`
- **SIFEN**: Tipo de contribuyente
- **Valores**:
  - `1` = Persona Física
  - `2` = Persona Jurídica
- **Obligatorio**: ✅ Sí

### param.tipoRegimen
- **ERPNext**: `Company.tipo_regimen`
- **SIFEN**: Tipo de régimen
- **Valores**: 1-8
  - 1 = Turismo
  - 2 = Importador
  - 3 = Exportador
  - 4 = Maquila
  - 5 = Ley 60/90
  - 6 = Pequeño Productor
  - 7 = Mediano Productor
  - 8 = Régimen Contable
- **Obligatorio**: ✅ Sí

### param.establecimientos[]
- **ERPNext**: `Company.codigo_establecimiento` + Address
- **SIFEN**: Array de establecimientos
- **Campos**:
  ```json
  {
    "codigo": "001",                    // Código de establecimiento (3 dígitos)
    "denominacion": "...",              // Denominación del establecimiento
    "direccion": "...",                 // Dirección (Address.line1)
    "numeroCasa": "123",                // Número de casa (Address.sifen_numero_casa)
    "complementoDireccion1": "...",     // Complemento (Address.line1)
    "complementoDireccion2": "...",     // Complemento 2 (Address.line2)
    "departamento": 12,                 // Departamento code (Address.state)
    "departamentoDescripcion": "...",   // Departamento description
    "distrito": 158,                    // Distrito code (Address.county)
    "distritoDescripcion": "...",       // Distrito description
    "ciudad": 5940,                     // Ciudad code (Address.city)
    "ciudadDescripcion": "...",         // Ciudad description
    "telefono": "...",                  // Teléfono (Address.phone)
    "email": "..."                      // Email (Address.email_id)
  }
  ```

---

## Sección DATA (Factura)

### data.tipoDocumento
- **ERPNext**: Determinado automáticamente según tipo de factura
- **SIFEN**: Tipo de documento
- **Valores**:
  - `1` = Factura electrónica
  - `5` = Nota de crédito electrónica
  - `6` = Nota de débito electrónica

### data.establecimiento
- **ERPNext**: `Company.codigo_establecimiento`
- **SIFEN**: Código de establecimiento
- **Formato**: String (3 dígitos, ej: "001")

### data.punto
- **ERPNext**: `Company.codigo_punto_expedicion_default` o `POS Profile.codigo_punto_expedicion`
- **SIFEN**: Punto de expedición
- **Formato**: String (3 dígitos, ej: "001")

### data.numero
- **ERPNext**: `Sales Invoice.name` (parseado)
- **SIFEN**: Número de factura
- **Formato**: String (últimos 7 dígitos)

### data.codigoSeguridadAleatorio
- **ERPNext**: `Sales Invoice.custom_numero_control` (auto-generado)
- **SIFEN**: Código de seguridad aleatorio
- **Formato**: String (9 dígitos, único por compañía)

### data.descripcion
- **ERPNext**: Determinado automáticamente
- **SIFEN**: Descripción del documento
- **Valores**:
  - "Factura electrónica"
  - "Nota de crédito electrónica"
  - "Nota de débito electrónica"

### data.observacion
- **ERPNext**: `Sales Invoice.remarks`
- **SIFEN**: Observaciones
- **Nota**: Se filtran textos por defecto como "no hay observaciones"

### data.fecha
- **ERPNext**: `Sales Invoice.posting_date`
- **SIFEN**: Fecha de emisión
- **Formato**: String (YYYY-MM-DDTHH:MM:SS)

### data.tipoEmision
- **ERPNext**: Tipo de Emisión en E-Invoice Setting
- **SIFEN**: Tipo de emisión
- **Valor**: `1` (Normal)

### data.tipoTransaccion
- **ERPNext**: `Sales Invoice.sifen_tipo_transaccion` / `POS Invoice.sifen_tipo_transaccion`
- **SIFEN**: Tipo de transacción
- **Valores**:
  - `1` = Venta de mercadería
  - `2` = Prestación de servicios
  - `3` = Mixto
  - `4` = Venta de activo fijo

### data.tipoImpuesto
- **ERPNext**: `Customer.sifen_tipo_impuesto`
- **SIFEN**: Tipo de impuesto
- **Valores**: 1-5 (ver tabla abajo)

---

## data.cliente (Cliente)

### data.cliente.contribuyente
- **ERPNext**: `Customer.sifen_contribuyente`
- **SIFEN**: ¿Es contribuyente?
- **Tipo**: Boolean (true/false)

### data.cliente.tipoOperacion
- **ERPNext**: `Customer.customer_group` → mapeado según la categoría
- **SIFEN**: Tipo de operación
- **Valores SIFEN v150**:
  - `1` = **B2B** — Venta entre contribuyentes (empresa → empresa)
  - `2` = **B2C** — Consumidor final (nacional o extranjero sin RUC)
  - `3` = **B2G** — Gobierno / Entidades públicas
  - `4` = **B2F** — **Fundaciones y Asociaciones sin fines de lucro**
- **Determinación**:
  ```
  Si customer_group = "Gobierno" o contiene "gubernamental" → 3 (B2G)
  Si customer_group = "Fundación" o "Asociación" → 4 (B2F)
  Si customer_group = "Consumidor Final" → 2 (B2C)
  Caso contrario → 1 (B2B)
  ```

### data.cliente.ruc
- **ERPNext**: `Customer.tax_id`
- **SIFEN**: RUC del cliente
- **Obligatorio**: Para B2B y B2G

### data.cliente.razonSocial
- **ERPNext**: `Customer.customer_name`
- **SIFEN**: Razón social

### data.cliente.nombreFantasia
- **ERPNext**: `Customer.customer_name`
- **SIFEN**: Nombre de fantasía

### data.cliente.direccion
- **ERPNext**: `Address.address_line1`
- **SIFEN**: Dirección

### data.cliente.numeroCasa
- **ERPNext**: `Address.sifen_numero_casa`
- **SIFEN**: Número de casa

### data.cliente.departamento / distrito / ciudad
- **ERPNext**: `Address.state` / `Address.county` / `Address.city`
- **SIFEN**: Códigos numéricos
- **Nota**: Para consumidor final extranjero son `null`

### data.cliente.pais
- **ERPNext**: `Address.country`
- **SIFEN**: Código ISO alpha-3 (ej: "PRY", "ARG")

### data.cliente.documentoTipo
- **ERPNext**: `Customer.sifen_tipo_documento`
- **SIFEN**: Tipo de documento
- **Valores**:
  - `1` = RUC
  - `2` = CI (Cédula de Identidad)
  - `3` = Pasaporte
  - `4` = Otro

### data.cliente.documentoNumero
- **ERPNext**: `Customer.tax_id` o `Customer.customer_name`
- **SIFEN**: Número de documento

### data.cliente.telefono
- **ERPNext**: `Address.phone` → fallback → `Customer.mobile_no`
- **SIFEN**: Teléfono

### data.cliente.celular
- **ERPNext**: `Address.phone` → fallback → `Customer.mobile_no`
- **SIFEN**: Celular

### data.cliente.email
- **ERPNext**: `Address.email_id` → fallback → `Customer.email_id`
- **SIFEN**: Email

---

## data.items[] (Items)

### items[].codigo
- **ERPNext**: `Sales Invoice Item.item_code`
- **SIFEN**: Código del item

### items[].descripcion
- **ERPNext**: `Sales Invoice Item.description` (sin HTML)
- **SIFEN**: Descripción

### items[].unidadMedida
- **ERPNext**: `Item.stock_uom` (mapeado)
- **SIFEN**: Código de unidad de medida
- **Mapeo común**:
  - "Nos" → 77 (Unidad)
  - "Kg" → 83 (Kilogramos)
  - "Litros" → 89 (Litros)
  - "Hora" → 100 (Hora)

### items[].cantidad
- **ERPNext**: `Sales Invoice Item.qty`
- **SIFEN**: Cantidad

### items[].precioUnitario
- **ERPNext**: `Sales Invoice Item.rate`
- **SIFEN**: Precio unitario

### items[].ivaTipo
- **ERPNext**: `Item Tax Template Detail.sifen_tipo_iva`
- **SIFEN**: Tipo de afectación al IVA
- **Valores**: 1-4

### items[].ivaProporcion
- **ERPNext**: Determinado según ivaTipo
- **SIFEN**: Proporción de IVA
- **Valores**:
  - 100 = Gravado
  - 0 = Exento/Exonerado

### items[].iva
- **ERPNext**: `Item Tax Template Detail.tax_rate`
- **SIFEN**: Tasa de IVA
- **Valores**: 10.0, 5.0, 0.0, etc.

---

## data.condicion (Condición de Pago)

### data.condicion.tipo
- **ERPNext**: Determinado automáticamente
- **SIFEN**: Tipo de condición
- **Valores**:
  - `1` = Si no existe términos de pago o se activa POS - Contado
  - `2` = Si existe términos de pago - Crédito

### data.condicion.credito.tipo
- **ERPNext**: Determinado según payment terms
- **SIFEN**: Tipo de crédito
- **Valores**:
  - `1` = Plazo (requiere `plazo`)
  - `2` = Cuota (requiere `cuotas`)

### data.condicion.credito.plazo
- **ERPNext**: `Payment Schedule.credit_days` o `Payment Term.days`
- **SIFEN**: Plazo en días
- **Obligatorio**: Si `credito.tipo = 1`
- **Formato**: 2-15 caracteres

---

## Tablas de Referencia

### Tipos de Impuesto (data.tipoImpuesto)

| Código | Descripción | Uso |
|--------|-------------|-----|
| 1 | IVA | Cliente local contribuyente |
| 2 | ISC | Productos con impuesto selectivo |
| 3 | Renta | Cliente extranjero con RUC |
| 4 | Ninguno | Cliente extranjero sin RUC |
| 5 | IVA-Renta | Mixto |

### Afectación al IVA (items[].ivaTipo)

| Código | Descripción | IVA Proporción |
|--------|-------------|----------------|
| 1 | Gravado IVA | 100% |
| 2 | Exonerado (Art.83) | 0% |
| 3 | Exento (no IVA) | 0% |
| 4 | Gravado parcial | Parcial |

### Tipos de Operación (data.cliente.tipoOperacion)

| Código | Tipo | RUC Requerido |
|--------|------|---------------|
| 1 | B2B | ✅ Sí |
| 2 | B2C | ❌ No |
| 3 | B2G | ✅ Sí |
| 4 | B2F | ❌ No (fundaciones) |

---

**Última actualización:** 2026-03-25
