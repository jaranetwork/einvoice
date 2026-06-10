# Nota de Remisión SIFEN (Delivery Note)

## ¿Qué es una Nota de Remisión SIFEN?

La Nota de Remisión (Delivery Note) es el documento electrónico que ampara el **traslado de bienes** desde el vendedor hasta el comprador. Se genera a partir de una **Sales Invoice** ya validada y aprobada por SIFEN, y se envía al sistema DTE-PY con la sección `transporte` que incluye datos del viaje, vehículo, transportista y chofer.

---

## Requisitos Previos

| Requisito | Detalle |
|-----------|---------|
| **Sales Invoice** | Validada (submit) con CDC de SIFEN |
| **Customer** | `sifen_codigo_cliente` auto-generado, dirección con departamento/distrito/ciudad |
| **Supplier transportista** | Opcional. Configurado con `sifen_contribuyente`, `sifen_tipo_documento`, dirección. Ver [Configuración del Proveedor](06a_supplier_setup.md) |
| **Vehicle** | Opcional. Con `sifen_vehiculo_tipo` y `sifen_documento_tipo`. Ver campos personalizados en Vehicle |
| **Driver** | Opcional. Con número de licencia |

---

## Paso a Paso

### 1. Crear Delivery Note desde Sales Invoice

```
Sales Invoice (validada) → Menú Crear → Nota de Entrega
```

Se crea una Delivery Note precargada con los datos de la factura.

### 2. Completar campos SIFEN en Delivery Note

| Campo | Valores |
|-------|---------|
| **SIFEN Motivo Nota de Remisión** | `1|Traslado por ventas`, `2|Traslado por consignación`, `3|Exporta` |
| **SIFEN Responsable Nota de Remisión** | `1|Emisor de la factura`, `2|Poseedor de la factura y bienes` |

### 3. Configurar Transportista (opcional)

En la sección **More Info → Información del transportista**, seleccionar un **Supplier** en el campo **Transporter**.

El transportista debe estar configurado con campos SIFEN (ver [Proveedor Transportista](06a_supplier_setup.md#proveedor-transportista-para-delivery-note--nota-de-remisi%C3%B3n)).

### 4. Guardar y Validar

```
Guardar (Borrador) → Validar (Submit)
```

### 5. Crear Viaje de Entrega

Ir a la pestaña **Conexiones** → click en **+** → seleccionar **Viaje de Entrega** (Delivery Trip).

### 6. Completar campos del Delivery Trip

| Campo | Descripción | Opciones |
|-------|-------------|----------|
| **Hora de Salida** | Fecha y hora de inicio del traslado | `YYYY-MM-DD HH:MM` |
| **SIFEN Transporte Tipo** | Tipo de transporte | `1|Propio`, `2|Tercero` |
| **SIFEN Transporte Modalidad** | Medio de transporte | `1|Terrestre`, `2|Fluvial`, `3|Aéreo`, `4|Multimodal` |
| **SIFEN Responsable del Flete** | Quién paga el flete | `1|Emisor`, `2|Receptor`, `3|Tercero`, `5|Transporte propio` |
| **SIFEN Distancia en Km** | Kilómetros recorridos | Número |
| **Vehículo** | Seleccionar Vehicle (opcional) | Vehículo con campos SIFEN |
| **Conductor** | Seleccionar Driver (opcional) | Driver con número de licencia |

### 7. Agregar Paradas de Entrega

En la tabla **Paradas de Entrega** (Delivery Stops):

1. Click en **Añadir Fila**
2. Seleccionar la **Delivery Note** vinculada
3. Completar **Llegada Estimada** (fecha y hora estimada de arribo)

### 8. Guardar Delivery Trip

```
Guardar
```

### 9. Generar E-Invoice

Volver a la **Delivery Note** y click en:

```
E-Invoice → Generate E-Invoice
```

> **Nota:** Si el Delivery Trip no existe, el sistema mostrará el error:
> *"Cannot generate E-Invoice without a Delivery Trip. Please create a Delivery Trip (Viaje de Entrega) with a Delivery Stop linked to this Delivery Note first."*

---

## Sección transporte en el Payload

Al generar la E-Invoice, el payload incluye la sección `transporte`:

```json
{
  "transporte": {
    "tipo": 1,
    "modalidad": 1,
    "tipoResponsable": 1,
    "inicioEstimadoTranslado": "2026-06-10 08:00",
    "finEstimadoTranslado": "2026-06-10 18:00",
    "salida": {
      "direccion": "Av. España 1234",
      "numeroCasa": "1234",
      "departamento": 1,
      "departamentoDescripcion": "CAPITAL",
      "distrito": 101,
      "distritoDescripcion": "ASUNCIÓN",
      "ciudad": 1,
      "ciudadDescripcion": "ASUNCIÓN"
    },
    "entrega": {
      "direccion": "Ruta 2 Km 18",
      "numeroCasa": "0",
      "departamento": 5,
      "departamentoDescripcion": "CORDILLERA",
      "distrito": 501,
      "distritoDescripcion": "CAACUPÉ",
      "ciudad": 1,
      "ciudadDescripcion": "CAACUPÉ"
    },
    "vehiculo": {
      "tipo": "CAMION",
      "marca": "Mercedes Benz",
      "documentoTipo": 2,
      "numeroMatricula": "ABC-1234"
    },
    "condicionNegociacion": "EXW",
    "transportista": {
      "contribuyente": true,
      "nombre": "TRANSPORTE RAPIDO S.R.L.",
      "direccion": "Av. Mariscal López 1234",
      "pais": "PRY",
      "ruc": "80098765-4",
      "chofer": {
        "nombre": "PEDRO RAMIREZ",
        "documentoNumero": "1234567"
      }
    }
  }
}
```

---

## Ejemplo Completo

### Prerrequisitos

- Sales Invoice: `ACC-SINV-2026-00060` (validada, CDC: `12345678901234567890`)
- Customer: DISTRIBUIDORA ABC S.A. (con `sifen_codigo_cliente` y dirección)
- Supplier: TRANSPORTE RAPIDO S.R.L. (transportista configurado)
- Vehicle: CAM-001 (tipo "CAMION", matrícula "ABC-1234")
- Driver: PEDRO RAMIREZ (licencia "1234567")

### Proceso

```
1. Sales Invoice ACC-SINV-2026-00060 → Crear → Nota de Entrega
2. Motivo: "1|Traslado por ventas"
3. Responsable: "1|Emisor de la factura"
4. Transporter: TRANSPORTE RAPIDO S.R.L.
5. Guardar → Validar (Submit)

6. Conexiones → + → Viaje de Entrega
   Hora de Salida: 2026-06-10 08:00
   SIFEN Transporte Tipo: "1|Propio"
   SIFEN Transporte Modalidad: "1|Terrestre"
   SIFEN Responsable del Flete: "1|Emisor"
   SIFEN Distancia en Km: 150
   Vehículo: CAM-001
   Conductor: PEDRO RAMIREZ

7. Paradas de Entrega:
   Delivery Note: [la creada]
   Llegada Estimada: 2026-06-10 18:00

8. Guardar Delivery Trip

9. Delivery Note → E-Invoice → Generate E-Invoice
```

---

## Referencias

- [Configuración del Proveedor Transportista](06a_supplier_setup.md#proveedor-transportista-para-delivery-note--nota-de-remisión)
- [Validaciones](06_validations.md)
- [Flujo de Trabajo](08_workflow.md)
- [Manual Técnico SIFEN v150](../../Manual_Técnico_Versión_150.md)

---

**Última actualización:** 2026-06-10
