# API SIFEN - Estructura del Payload

Este documento describe la estructura completa del payload enviado a la API DTE-PY.

---

## Endpoint

```
POST {BASE_URL}/api/facturar/crear
```

**Headers:**
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer {API_KEY}"
}
```

---

## Estructura del Request

```json
{
  "param": { ... },  // Datos de la empresa/emisor
  "data": { ... }    // Datos de la factura
}
```

---

## Sección PARAM

### Estructura Completa

```json
{
  "version": 150,
  "ruc": "123456-1",
  "razonSocial": "EMPRESA S.A.",
  "nombreFantasia": "EMPRESA",
  "actividadesEconomicas": [
    {
      "codigo": "01110",
      "descripcion": "Cultivo de cereales"
    }
  ],
  "timbradoNumero": "123456789",
  "timbradoFecha": "2024-01-01",
  "tipoContribuyente": 2,
  "tipoRegimen": 8,
  "establecimientos": [
    {
      "codigo": "001",
      "denominacion": "Casa Central",
      "direccion": "Av. Principal 123",
      "numeroCasa": "123",
      "complementoDireccion1": "Edificio XYZ",
      "complementoDireccion2": "Piso 2",
      "departamento": 12,
      "departamentoDescripcion": "CENTRAL",
      "distrito": 158,
      "distritoDescripcion": "LIMPIO",
      "ciudad": 5940,
      "ciudadDescripcion": "LIMPIO (MUNICIPIO)",
      "telefono": "+595 981 123456",
      "email": "info@empresa.com"
    }
  ]
}
```

### Campos del PARAM

| Campo | Tipo | Obligatorio | Descripción | Ejemplo |
|-------|------|-------------|-------------|---------|
| `version` | int | ✅ | Versión del manual | `150` |
| `ruc` | string | ✅ | RUC de la empresa | `"123456-1"` |
| `razonSocial` | string | ✅ | Razón social | `"EMPRESA S.A."` |
| `nombreFantasia` | string | ✅ | Nombre de fantasía | `"EMPRESA"` |
| `actividadesEconomicas` | array | ✅ | Actividades (≥1) | `[...]` |
| `timbradoNumero` | string | ✅ | Número de timbrado | `"123456789"` |
| `timbradoFecha` | string | ✅ | Fecha de timbrado | `"2024-01-01"` |
| `tipoContribuyente` | int | ✅ | 1=Física, 2=Jurídica | `2` |
| `tipoRegimen` | int | ✅ | 1-8 | `8` |
| `establecimientos` | array | ✅ | Lista de establecimientos | `[...]` |

---

## Sección DATA

### Estructura Completa

```json
{
  "tipoDocumento": 1,
  "establecimiento": "001",
  "punto": "001",
  "numero": "00000001",
  "codigoSeguridadAleatorio": "123456789",
  "descripcion": "Factura electrónica",
  "observacion": "",
  "fecha": "2026-03-25T10:30:00",
  "tipoEmision": 1,
  "tipoTransaccion": 1,
  "tipoImpuesto": 1,
  "moneda": "PYG",
  "condicionAnticipo": 1,
  "condicionTipoCambio": 1,
  "descuentoGlobal": 0,
  "anticipoGlobal": 0,
  "cliente": { ... },
  "usuario": { ... },
  "factura": { ... },
  "condicion": { ... },
  "items": [ ... ],
  "totalPago": 120000
}
```

### Campos Principales de DATA

| Campo | Tipo | Obligatorio | Descripción | Ejemplo |
|-------|------|-------------|-------------|---------|
| `tipoDocumento` | int | ✅ | 1=Factura, 5=NC, 6=ND | `1` |
| `establecimiento` | string | ✅ | Código (3 dígitos) | `"001"` |
| `punto` | string | ✅ | Punto de expedición | `"001"` |
| `numero` | string | ✅ | Número de factura | `"00000001"` |
| `codigoSeguridadAleatorio` | string | ✅ | 9 dígitos único | `"123456789"` |
| `descripcion` | string | ✅ | Tipo de documento | `"Factura electrónica"` |
| `observacion` | string | ❌ | Observaciones | `""` |
| `fecha` | string | ✅ | Fecha y hora | `"2026-03-25T10:30:00"` |
| `tipoEmision` | int | ✅ | 1=Normal | `1` |
| `templateFactura` | string | ❌ | Tipo de template: `"normal"` o `"ticket"` | `"normal"` |
| `tipoTransaccion` | int | ✅ | 1=Mercadería, 2=Servicios | `1` |
| `tipoImpuesto` | int | ✅ | 1-5 | `1` |
| `moneda` | string | ✅ | ISO 4217 | `"PYG"` |
| `condicionAnticipo` | int | ✅ | 1=Global, 2=Por ítem | `1` |
| `condicionTipoCambio` | int | ✅ | 1=Global, 2=Por ítem | `1` |
| `descuentoGlobal` | float | ❌ | Descuento global | `0` |
| `anticipoGlobal` | float | ❌ | Anticipo global | `0` |
| `cliente` | object | ✅ | Datos del cliente | `{...}` |
| `usuario` | object | ✅ | Datos del usuario | `{...}` |
| `factura` | object | ✅ | Datos de factura | `{...}` |
| `condicion` | object | ✅ | Condición de pago | `{...}` |
| `items` | array | ✅ | Items de la factura | `[...]` |
| `totalPago` | float | ✅ | Total a pagar | `120000` |

---

## data.cliente

### Estructura

```json
{
  "contribuyente": true,
  "tipoOperacion": 1,
  "ruc": "123456-1",
  "razonSocial": "CLIENTE S.A.",
  "nombreFantasia": "CLIENTE",
  "direccion": "Av. España 456",
  "numeroCasa": "456",
  "complementoDireccion1": "Oficina 2",
  "departamento": 1,
  "departamentoDescripcion": "ASUNCION",
  "distrito": 1,
  "distritoDescripcion": "ASUNCION",
  "ciudad": 1,
  "ciudadDescripcion": "ASUNCION",
  "pais": "PRY",
  "paisDescripcion": "Paraguay",
  "tipoContribuyente": 1,
  "documentoTipo": 1,
  "documentoNumero": "123456-1",
  "telefono": "+595 981 654321",
  "celular": "+595 981 654321",
  "email": "cliente@email.com",
  "codigo": ""
}
```

### Campos del Cliente

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `contribuyente` | boolean | ✅ | true/false |
| `tipoOperacion` | int | ✅ | 1=B2B, 2=B2C, 3=B2G, 4=B2F |
| `ruc` | string | ✅ Para B2B/B2G | RUC del cliente |
| `razonSocial` | string | ✅ | Razón social |
| `nombreFantasia` | string | ❌ | Nombre de fantasía |
| `direccion` | string | ✅ | Dirección completa |
| `numeroCasa` | string | ❌ | Número de casa |
| `complementoDireccion1` | string | ❌ | Complemento dirección |
| `departamento` | int/null | ✅ (Paraguay) | Código de departamento (1-17) |
| `departamentoDescripcion` | string | ✅ (Paraguay) | Nombre del departamento |
| `distrito` | int/null | ✅ (Paraguay) | Código de distrito |
| `distritoDescripcion` | string | ✅ (Paraguay) | Nombre del distrito |
| `ciudad` | int/null | ✅ (Paraguay) | Código de ciudad |
| `ciudadDescripcion` | string | ✅ (Paraguay) | Nombre de la ciudad |
| `pais` | string | ✅ | ISO alpha-3 (PRY para Paraguay) |
| `paisDescripcion` | string | ✅ | Nombre del país |
| `tipoContribuyente` | int | ✅ | 1=Company, 2=Individual |
| `documentoTipo` | int | ✅ | 1=RUC, 2=CI, 3=Pasaporte, 4=Otros |
| `documentoNumero` | string | ✅ | Número de documento |
| `telefono` | string | ❌ | Teléfono fijo |
| `celular` | string | ❌ | Teléfono celular |
| `email` | string | ❌ | Email |
| `codigo` | string | ❌ | Código de cliente |

### Notas sobre Ubicación (Paraguay)

Para clientes en Paraguay, los campos de ubicación se obtienen del Address:

- **departamento**: Código numérico del departamento (ej: 1=ASUNCION, 12=CENTRAL)
- **distrito**: Código numérico del distrito (se obtiene del campo `county` en Address)
- **ciudad**: Código numérico de la ciudad (se obtiene del campo `city` en Address)

**Importante:** El campo `county` en Address contiene el distrito con formato `"codigo|nombre"` (ej: `"1|ASUNCION"`).

---

## data.items[]

### Estructura

```json
[
  {
    "codigo": "PRODUCTO-001",
    "descripcion": "Producto Ejemplo",
    "observacion": "",
    "unidadMedida": 77,
    "cantidad": 10,
    "precioUnitario": 10000,
    "cambio": 0,
    "descuento": 0,
    "anticipo": 0,
    "pais": "PRY",
    "paisDescripcion": "Paraguay",
    "ivaTipo": 1,
    "ivaProporcion": 100,
    "iva": 10.0
  }
]
```

### Campos del Item

| Campo | Tipo | Obligatorio | Descripción | Ejemplo |
|-------|------|-------------|-------------|---------|
| `codigo` | string | ✅ | Código del item | `"PRODUCTO-001"` |
| `descripcion` | string | ✅ | Descripción | `"Producto Ejemplo"` |
| `observacion` | string | ❌ | Observación | `""` |
| `unidadMedida` | int | ✅ | Código UOM SIFEN | `77` |
| `cantidad` | float | ✅ | Cantidad | `10` |
| `precioUnitario` | float | ✅ | Precio unitario | `10000` |
| `cambio` | float | ✅ | Tipo de cambio | `0` (PYG) |
| `descuento` | float | ❌ | Descuento | `0` |
| `anticipo` | float | ❌ | Anticipo | `0` |
| `pais` | string | ❌ | ISO alpha-3 | `"PRY"` |
| `ivaTipo` | int | ✅ | 1-4 | `1` |
| `ivaProporcion` | int | ✅ | 0 o 100 | `100` |
| `iva` | float | ✅ | Tasa de IVA | `10.0` |

### Códigos de Unidad de Medida (unidadMedida)

| Código | Descripción | UOM ERPNext |
|--------|-------------|-------------|
| 77 | Unidad | Nos, Unidad |
| 83 | Kilogramos | Kg |
| 86 | Gramos | Gr |
| 89 | Litros | Litros, Lt |
| 100 | Hora | Hora, Hr |
| 102 | Día | Día |
| 108 | Metros | M, Metro |

---

## data.condicion

### Estructura (Contado)

```json
{
  "tipo": 1,
  "entregas": [
    {
      "tipo": 1,
      "monto": "120000",
      "moneda": "PYG",
      "cambio": 0
    }
  ]
}
```

### Estructura (Crédito - Plazo)

```json
{
  "tipo": 2,
  "credito": {
    "tipo": 1,
    "plazo": "30",
    "dDCondCred": "Plazo"
  },
  "entregas": [
    {
      "tipo": 2,
      "monto": "120000",
      "moneda": "PYG",
      "cambio": 0
    }
  ]
}
```

### Estructura (Crédito - Cuotas)

```json
{
  "tipo": 2,
  "credito": {
    "tipo": 2,
    "cuotas": [
      {
        "numero": 1,
        "monto": 40000,
        "fecha": "2026-04-24"
      },
      {
        "numero": 2,
        "monto": 40000,
        "fecha": "2026-05-24"
      },
      {
        "numero": 3,
        "monto": 40000,
        "fecha": "2026-06-24"
      }
    ]
  },
  "entregas": [
    {
      "tipo": 2,
      "monto": "40000",
      "moneda": "PYG",
      "cambio": 0
    },
    {
      "tipo": 2,
      "monto": "40000",
      "moneda": "PYG",
      "cambio": 0
    },
    {
      "tipo": 2,
      "monto": "40000",
      "moneda": "PYG",
      "cambio": 0
    }
  ]
}
```

### Campos de Condición

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `tipo` | int | ✅ | 1=Contado, 2=Crédito |
| `credito.tipo` | int | ✅ Si tipo=2 | 1=Plazo, 2=Cuotas |
| `credito.plazo` | string | ✅ Si credito.tipo=1 | Días (2-15 caracteres) |
| `credito.cuotas` | array | ✅ Si credito.tipo=2 | Array de cuotas |
| `entregas` | array | ✅ | Entregas de pago |

### Campos de Entregas

Cada entrega en el array `entregas` debe tener exactamente estos 4 campos:

| Campo | Tipo | Obligatorio | Descripción | Ejemplo |
|-------|------|-------------|-------------|---------|
| `tipo` | int | ✅ | Tipo de pago: 1=Contado, 2=Crédito, 5=Anticipo | `1` |
| `monto` | string | ✅ | Monto de la entrega | `"120000"` |
| `moneda` | string | ✅ | Código de moneda ISO | `"PYG"` |
| `cambio` | int | ✅ | Tipo de cambio (0 si PYG) | `0` |

**Nota:** Los campos `numero` y `fecha` **no se incluyen** en las entregas según el estándar SIFEN.

---

## data.usuario

### Estructura

```json
{
  "documentoTipo": 1,
  "documentoNumero": "123456-1",
  "nombre": "Juan Pérez",
  "cargo": "Gerente General"
}
```

### Campos

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `documentoTipo` | int | ✅ | 1=RUC, 2=CI, etc. |
| `documentoNumero` | string | ✅ | Número de documento |
| `nombre` | string | ✅ | Nombre completo |
| `cargo` | string | ✅ | Cargo |

---

## Respuesta de la API

### Éxito (200)

```json
{
  "success": true,
  "message": "Factura encolada para procesamiento asíncrono",
  "data": {
    "facturaId": "65f1234567890abcdef12345",
    "correlativo": "001-001-00000060",
    "estado": "encolado",
    "cdc": "ABC123456789",
    "jobId": "factura-65f1234567890abcdef12345",
    "xmlLink": "https://...",
    "kudeLink": "https://...",
    "urls": {
      "estado": "https://...",
      "consulta": "https://..."
    }
  }
}
```

### Error (400/500)

```json
{
  "success": false,
  "message": "Error description",
  "error": "Detailed error"
}
```

---

## Referencias

- [Campos SIFEN](02_sifen_fields.md)
- [Configuración de la Empresa](03_company_setup.md)
- [Configuración del Customer](04_customer_setup.md)
- [Manual Técnico SIFEN v150](../../Manual_Técnico_Versión_150.md)

---

**Última actualización:** 2026-03-28
