# Validaciones Automáticas

Este documento describe todas las validaciones automáticas que se ejecutan al guardar/validar una Sales Invoice.

---

## Ejecución de Validaciones

### Cuándo se Ejecutan

Las validaciones se ejecutan en el evento **`validate`** de Sales Invoice:

```python
# hooks.py
doc_events = {
    "Sales Invoice": {
        "validate": [
            "einvoice.e_invoice.utils.api_client.asignar_numero_control",
            "einvoice.e_invoice.utils.api_client.validar_campos_sifen",
        ],
    }
}
```

### Orden de Ejecución

1. **`asignar_numero_control()`** → Genera número de control (9 dígitos)
2. **`validar_campos_sifen()`** → Valida todos los campos SIFEN

### Cuándo se Disparan

| Acción | ¿Ejecuta Validaciones? |
|--------|----------------------|
| Guardar (Borrador) | ✅ Sí |
| Validar (Submit) | ✅ Sí |
| Actualizar (Validada) | ✅ Sí |
| Cancelar | ❌ No |

---

## Validaciones por Entidad

### 1. Company (Empresa)

| Campo | Validación | Error si falla |
|-------|-----------|----------------|
| Tax ID (RUC) | No vacío | "Company Tax ID (RUC) is missing in Company {0}" |
| Codigo Establecimiento | No vacío, ≤3 dígitos | "El Código de Establecimiento está vacío" / "no puede superar 3 dígitos" |
| Numero Timbrado | No vacío | "El Número de Timbrado está vacío" |
| Fecha Timbrado | No vacío | "La Fecha de Timbrado está vacía" |
| Tipo Contribuyente | 1 o 2 | "El Tipo de Contribuyente está vacío" |
| Tipo Regimen | 1-8 | "El Tipo de Régimen está vacío" |
| Actividades Económicas | ≥1 fila | "No hay Actividades Económicas configuradas" |
| Actividad (cada fila) | codigo_actividad no vacío | "La Actividad Económica #{0} no tiene código" |
| Actividad (cada fila) | descripcion_actividad no vacío | "La Actividad Económica #{0} no tiene descripción" |
| Responsable (tipo) | No vacío | "El Tipo de Documento del Responsable SIFEN está vacío" |
| Responsable (número) | No vacío | "El Número de Documento del Responsable SIFEN está vacío" |
| Responsable (nombre) | No vacío | "El Nombre del Responsable SIFEN está vacío" |
| Responsable (cargo) | No vacío | "El Cargo del Responsable SIFEN está vacío" |

---

### 2. Customer (Cliente)

| Campo | Validación | Error si falla |
|-------|-----------|----------------|
| Customer | No vacío | "El cliente es obligatorio" |
| sifen_tipo_documento | No vacío | "El SIFEN Tipo Documento del cliente está vacío" |
| sifen_tipo_impuesto | No vacío | "El SIFEN Tipo Impuesto del cliente está vacío" |
| sifen_tipo_documento (B2B/B2G) | = "1" | "El cliente para operación {0} debe tener SIFEN Tipo Documento = 'RUC'" |
| sifen_tipo_documento (B2C) | = "1" o "2" | "El cliente para operación B2C debe tener SIFEN Tipo Documento = 'RUC' o 'CI'" |
| sifen_tipo_documento (B2F) | = "3" o "4" | "El cliente extranjero (B2F) debe tener SIFEN Tipo Documento = 'Pasaporte' o 'Otro'" |
| sifen_tipo_impuesto (Paraguay) | 1, 2, o 5 | "El SIFEN Tipo Impuesto no es coherente con el tipo de operación" |
| sifen_tipo_impuesto (B2F) | 3 o 4 | "El SIFEN Tipo Impuesto no es coherente con el tipo de operación" |
| Tax ID (B2B/B2G) | No vacío | "El RUC del cliente es obligatorio para operación {0}" |

---

### 3. Address (Dirección del Cliente)

| Campo | Validación | Error si falla |
|-------|-----------|----------------|
| State (Paraguay) | No vacío, formato correcto | "El Departamento (State) es obligatorio" / "debe estar en formato '1\|CAPITAL' o '1'" |
| County (Paraguay) | No vacío | "El Distrito (County) es obligatorio" |
| City (Paraguay) | No vacío | "La Ciudad (City) es obligatoria" |
| Country (B2F) | ≠ Paraguay | "La operación B2F (Extranjero) requiere un país diferente a Paraguay" |

---

### 4. Items

| Campo | Validación | Error si falla |
|-------|-----------|----------------|
| Item Code | No vacío | "El código del item es obligatorio para el item #{0}" |
| Rate | No vacío | "El precio unitario es obligatorio para el item #{0}" |
| Qty | No vacío | "La cantidad es obligatoria para el item #{0}" |
| Item Tax Template | Configurado | "El item #{0} no tiene Plantilla de Impuesto configurada" |
| Tax Template Lines | ≥1 línea | "La Plantilla de Impuesto '{0}' no tiene líneas de impuesto configuradas" |
| sifen_tipo_iva | Configurado (1-4) | "La Plantilla no tiene 'SIFEN Tipo IVA' configurado" / "valor inválido" |
| tax_rate (Paraguay, gravado) | > 0% | "La Plantilla tiene todos los impuestos con tasa 0%" |

---

### 5. Sales Taxes and Charges

| Validación | Descripción | Error si falla |
|-----------|-------------|----------------|
| No vacío (Paraguay) | La tabla no debe estar vacía | "La factura no tiene impuestos configurados en la tabla 'Sales Taxes and Charges'" |
| tax_rate > 0% | Impuestos gravados deben tener tasa > 0 | "La factura tiene impuestos con tasa 0%" |

---

### 6. Payment Schedule (Términos de Pago)

| Validación | Descripción | Error si falla |
|-----------|-------------|----------------|
| Payment Terms/Advances | Al menos uno configurado | "La factura no tiene Términos de Pago ni Adelantos configurados" |
| credit_days (Crédito) | > 0 si es operación a crédito | "La factura es una operación a Crédito pero no tiene plazo configurado" |

---

### 7. Número de Control

| Campo | Validación | Error si falla |
|-------|-----------|----------------|
| custom_numero_control | 9 dígitos | "El Número de Control debe tener exactamente 9 dígitos" |
| custom_numero_control | Solo números | "El Número de Control debe contener solo dígitos" |

---

### 8. Notas de Crédito y Débito (NC/ND)

| Validación | Descripción | Error si falla |
|-----------|-------------|----------------|
| return_against | Obligatorio para NC/ND | "Credit/Debit Note must reference an original invoice in 'Return Against' field" |
| CDC en factura original | La factura referenciada debe tener CDC | "Original invoice {0} does not have a CDC (Código de Control). The referenced invoice must have a valid CDC from SIFEN before creating a Credit/Debit Note." |
| sifen_motivo_nota_credito_debito | Obligatorio para NC/ND | "El motivo de la Nota de Crédito/Débito es obligatorio" |

---

### 9. Campo "Incluir Pago Después de Validar"

Este campo permite validar facturas **de Contado** sin pagos registrados, pero **bloquea el envío a FEPY** hasta que se registren los pagos.

| Validación | Descripción | Error si falla |
|-----------|-------------|----------------|
| is_pos AND incluir_pago_despues_validar | Solo uno puede estar marcado | "Only one of the following options can be selected: Include Payment (POS) or Include Payment After Validate" |
| incluir_pago_despues_validar + Sin pagos | Bloquea envío a FEPY | "Agrega un pago en Entrada de Pago para enviar a FEPY." |

**Propósito:**
- Permitir validar facturas de Contado sin pagos (útil cuando el pago se registra después)
- Bloquear el envío a FEPY hasta que existan Payment Entries vinculados

**Flujo correcto:**
1. Marcar "Incluir Pago Después de Validar" (en Borrador)
2. Validar factura (Submit) ✅
3. Crear Payment Entry contra la factura
4. Click en "Generar E-Invoice" ✅

**Nota:** Para facturas a **Crédito**, este campo **no es necesario** - se puede enviar a FEPY sin pagos registrados.

---

## Validaciones por Tipo de Operación

### B2B (tipoOperacion = 1)

| Validación | Descripción |
|-----------|-------------|
| Customer RUC | Obligatorio |
| Customer sifen_tipo_documento | Debe ser "1" (RUC) |
| Customer sifen_tipo_impuesto | 1, 2, o 5 (NO 3 o 4) |
| Address (Paraguay) | Departamento, Distrito, Ciudad obligatorios |
| Payment Terms | Requerido si es crédito |
| credit_days | > 0 si es crédito |

---

### B2C (tipoOperacion = 2)

| Validación | Descripción |
|-----------|-------------|
| Customer RUC | NO obligatorio |
| Customer sifen_tipo_documento | "1" (RUC) o "2" (CI) |
| Customer sifen_tipo_impuesto | 1, 2, o 5 (NO 3 o 4) |
| Address (Paraguay) | Departamento, Distrito, Ciudad obligatorios |
| Payment Terms | Requerido si es crédito |

---

### B2G (tipoOperacion = 3)

| Validación | Descripción |
|-----------|-------------|
| Customer RUC | Obligatorio |
| Customer sifen_tipo_documento | Debe ser "1" (RUC) |
| Customer sifen_tipo_impuesto | 1, 2, o 5 (NO 3 o 4) |
| Address (Paraguay) | Departamento, Distrito, Ciudad obligatorios |
| Payment Terms | Requerido si es crédito |

---

### B2F (tipoOperacion = 4)

| Validación | Descripción |
|-----------|-------------|
| Customer Country | ≠ Paraguay |
| Customer sifen_contribuyente | Debe ser NO (False) |
| Customer sifen_tipo_documento | "3" (Pasaporte) o "4" (Otro) |
| Customer sifen_tipo_impuesto | 3 o 4 (NO 1, 2, o 5) |
| Address | Departamento/Distrito/Ciudad = null |

---

## Mensajes de Error

### Formato de Errores

Los errores se muestran en un solo mensaje con formato HTML:

```
[Error 1]<br><br>[Error 2]<br><br>[Error 3]...
```

### Ejemplo de Mensaje Múltiple

```
El SIFEN Tipo Documento del cliente está vacío.

Cliente: JUAN PEREZ

Por favor, seleccione el tipo de documento en el campo 'SIFEN Tipo Documento' en el registro del cliente.

Opciones:
1 = RUC (para contribuyentes)
2 = CI (Cédula de Identidad)
3 = Pasaporte
4 = Otro

<br><br>

El SIFEN Tipo Impuesto del cliente está vacío.

Por favor, seleccione el tipo de impuesto en el campo 'SIFEN Tipo Impuesto' en el registro del cliente.

Opciones:
1 = IVA (cliente local contribuyente)
2 = ISC (productos con impuesto selectivo)
3 = Renta (cliente extranjero B2F con RUC)
4 = Ninguno (cliente extranjero sin RUC, consumidor final)
5 = IVA - Renta (mixto)
```

---

## Flujo de Validación

```
Sales Invoice.validate()
    ↓
asignar_numero_control()
    ↓ (genera número de control si no existe)
validar_campos_sifen()
    ↓
├── Validar Company
│   ├── Tax ID
│   ├── Codigo Establecimiento
│   ├── Timbrado
│   ├── Actividades Económicas
│   └── Responsable SIFEN
├── Validar Customer
│   ├── sifen_tipo_documento
│   ├── sifen_tipo_impuesto
│   └── tipoOperacion (automático)
├── Validar Address
│   ├── Departamento
│   ├── Distrito
│   └── Ciudad
├── Validar Items
│   ├── Item Tax Template
│   ├── sifen_tipo_iva
│   └── tax_rate
├── Validar Sales Taxes
│   └── tax_rate > 0%
├── Validar Payment Schedule
│   ├── Payment Terms/Advances
│   └── credit_days (si crédito)
└── Validar Número de Control
    └── 9 dígitos
    ↓
Si hay errores → frappe.throw()
Si todo OK → continuar con save/submit
```

---

## Cómo Depurar Validaciones

### 1. Ver Logs en Consola

Si hay errores de Python, revisar la consola de `bench start`:

```bash
bench start
# En otra terminal, guardar la factura
# Ver errores en la consola
```

### 2. Ver Error Log

```
Menu → Settings → Error Log
```

Buscar errores con título "E-Invoice".

### 3. Probar Validación Individual

```python
# En bench console
bench --site development.localhost console

from einvoice.e_invoice.utils.api_client import validar_campos_sifen
doc = frappe.get_doc("Sales Invoice", "ACC-SINV-2026-00001")
validar_campos_sifen(doc)
```

---

## Referencias

- [Configuración de la Empresa](03_company_setup.md)
- [Configuración del Customer](04_customer_setup.md)
- [Configuración de Items](05_items_setup.md)
- [Campos SIFEN](02_sifen_fields.md)

---

**Última actualización:** 2026-03-28
