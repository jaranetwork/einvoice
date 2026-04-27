# Flujo de Trabajo (Workflow)

Este documento describe el flujo completo de trabajo con el módulo E-Invoice.

---

## Flujo Completo de Facturación

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. CONFIGURACIÓN INICIAL                                        │
│    - Company (RUC, Timbrado, Actividades)                      │
│    - Customer (tipo_documento, tipo_impuesto)                  │
│    - Items (Item Tax Template con sifen_tipo_iva)              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. CREAR SALES INVOICE                                          │
│    - Seleccionar Customer                                       │
│    - Agregar Items                                              │
│    - Verificar Payment Terms (si crédito)                       │
│    - Guardar (Borrador)                                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. VALIDAR FACTURA (SUBMIT)                                     │
│    - Ejecuta validaciones automáticas                           │
│    - Genera Número de Control (9 dígitos)                       │
│    - Valida campos SIFEN                                        │
│    - Si hay errores → Mostrar mensaje                           │
│    - Si todo OK → DocStatus = 1                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. ENVIAR A FEPY                                               │
│    - Menú E-Invoice → Generar E-Invoice                             │
│    - Construye payload (param + data)                           │
│    - Envía a API externa                                        │
│    - Guarda respuesta en factura                                │
│    - Muestra mensaje de éxito/error                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. DESCARGAR DOCUMENTOS                                         │
│    - Download XML (XML de la factura)                           │
│    - Download KUDE (PDF representativo)                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Paso 1: Configuración Inicial

### 1.1 Configurar Company

Ver [Configuración de la Empresa](03_company_setup.md)

**Campos críticos:**
- Tax ID (RUC)
- Timbrado (número y fecha)
- Actividades Económicas (≥1)
- Responsable SIFEN

### 1.2 Configurar Customer

Ver [Configuración del Customer](04_customer_setup.md)

**Campos críticos:**
- sifen_tipo_documento
- sifen_tipo_impuesto
- Address con Departamento/Distrito/Ciudad

### 1.3 Configurar Items

Ver [Configuración de Items](05_items_setup.md)

**Campos críticos:**
- Item Tax Template con sifen_tipo_iva (1-4)
- tax_rate > 0% (para items gravados)

---

## Paso 2: Crear Sales Invoice

### 2.1 Nueva Factura

```
Menu → Accounting → Sales Invoice → Add Sales Invoice
```

### 2.2 Completar Campos

1. **Customer**: Seleccionar customer configurado
2. **Items**: Agregar items con cantidades y precios
3. **Payment Terms** (si es crédito):
   - Seleccionar Payment Terms Template, o
   - Agregar términos manualmente

### 2.3 Guardar como Borrador

```
Click en Save (o Ctrl+S)
```

**Estado**: DocStatus = 0 (Borrador)

---

## Paso 3: Validar Factura (Submit)

### 3.1 Click en Validate

```
Click en Validate (Submit)
```

### 3.2 Validaciones Automáticas

El sistema ejecuta:

1. **`asignar_numero_control()`**:
   - Genera número de control único (9 dígitos)
   - Verifica unicidad en DB

2. **`validar_campos_sifen()`**:
   - Valida Company (RUC, Timbrado, etc.)
   - Valida Customer (tipo_documento, tipo_impuesto)
   - Valida Address (Departamento, Distrito, Ciudad)
   - Valida Items (Item Tax Template, sifen_tipo_iva)
   - Valida Sales Taxes (tax_rate > 0%)
   - Valida Payment Schedule (credit_days si crédito)

### 3.3 Campo "Incluir Pago Después de Validar"

Para facturas **de Contado** sin pagos registrados:

1. **Marcar el campo** (antes de validar):
   ```
   Incluir Pago Después de Validar = ✓
   ```

2. **Validar factura**:
   - ✅ Permite validar sin pagos
   - DocStatus = 1

3. **Agregar pago después**:
   - Crear Payment Entry contra la factura, o
   - Agregar en tabla Payments

4. **Enviar a FEPY**:
   - El sistema verifica que existan pagos
   - Si no hay pagos → Error: "Agrega un pago en Entrada de Pago para enviar a FEPY"

**Nota:** Para facturas a **Crédito**, este campo **no es necesario**.

### 3.4 Resultado

**Si hay errores:**
```
Mensaje de error con lista de campos faltantes
La factura permanece en borrador
```

**Si todo está correcto:**
```
Factura validada
DocStatus = 1
Número de Control asignado
```

---

## Paso 4: Enviar a SIFEN

### 4.1 Menú E-Invoice

Con la factura validada:

```
Menú → E-Invoice → Send to SIFEN
```

### 4.2 Proceso de Envío

1. **Extraer datos** de la factura
2. **Construir payload**:
   - param (datos de empresa)
   - data (datos de factura)
3. **Enviar a API** externa
4. **Guardar respuesta**:
   - custom_sifen_factura_id
   - custom_sifen_correlativo
   - custom_sifen_estado
   - custom_sifen_cdc
5. **Mostrar mensaje** de éxito/error

### 4.3 Resultado

**Éxito:**
```
✓ E-Invoice Generated Successfully

Factura ID: 65f1234567890abcdef12345
Correlativo: 001-001-00000060
Estado: encolado
CDC: ABC123456789
```

**Error:**
```
Error generating E-Invoice: [detalle del error]
```

---

## Paso 5: Descargar Documentos

### 5.1 Download XML

```
Menú → E-Invoice → Download XML
```

**Resultado**: Descarga archivo `.xml` con el contenido de la factura electrónica.

### 5.2 Download KUDE

```
Menú → E-Invoice → Download KUDE
```

**Resultado**: Descarga archivo `.pdf` con la representación gráfica (KUDE).

---

## Estados de la Factura

### Estados en ERPNext

| DocStatus | Estado | Descripción |
|-----------|--------|-------------|
| 0 | Borrador | Factura no validada |
| 1 | Validada | Factura submitida |
| 2 | Cancelada | Factura cancelada |

### Estados en FEPY - SIFEN

| Estado | Descripción |
|--------|-------------|
| encolado | Factura en cola de procesamiento |
| aprobado | Factura aprobada por SIFEN |
| rechazado | Factura rechazada por SIFEN |
| anulado | Factura anulada |

---

## Botones Disponibles

### En Borrador (DocStatus = 0)

| Botón | Menú | Acción |
|-------|------|--------|
| Save | - | Guardar borrador |
| Validate | - | Validar (Submit) |

### En Validada (DocStatus = 1)

| Botón | Menú | Visible | Acción |
|-------|------|---------|--------|
| Generar E-Invoice | E-Invoice | Todos | Enviar a FEPY |
| Regenerate and Send | E-Invoice | Administrator | Regenerar y reenviar |
| Download XML | E-Invoice | Todos | Descargar XML |
| Download KUDE | E-Invoice | Todos | Descargar KUDE |
| Check Local Status | E-Invoice | Todos | Ver estado local |
| Refresh Status | E-Invoice | Todos | Actualizar desde FEPY |

---

## Escenarios Comunes

### Escenario 1: Factura Contado (B2B)

```
1. Crear Sales Invoice
2. Customer: Empresa S.A. (B2B, con RUC)
3. Items: Productos con IVA 10%
4. Payment Terms: No requiere (contado)
5. Validate → OK
6. Generar E-Invoice → OK
7. Download XML/KUDE
```

### Escenario 2: Factura Crédito (B2B)

```
1. Crear Sales Invoice
2. Customer: Empresa S.A. (B2B, con RUC)
3. Items: Productos con IVA 10%
4. Payment Terms: 30 días (credit_days = 30)
5. Validate → Valida credit_days > 0
6. Generar E-Invoice → data.condicion.credito.tipo = 1, plazo = "30"
7. Download XML/KUDE
```

### Escenario 3: Factura B2C (Consumidor Final)

```
1. Crear Sales Invoice
2. Customer: Juan Pérez (B2C, sin RUC)
3. Items: Productos con IVA 10%
4. Payment Terms: Contado
5. Validate → Valida tipo_documento = "2" (CI)
6. Generar E-Invoice → tipoOperacion = 2, tipoImpuesto = 4
7. Download XML/KUDE
```

### Escenario 4: Nota de Crédito

```
1. Crear Sales Invoice
2. Is Return: Yes
3. Return Against: [Factura original]
4. Items: Mismos items (negativos)
5. Validate → OK
6. Generar E-Invoice → tipoDocumento = 5
7. Download XML/KUDE
```

---

## Errores Comunes y Soluciones

### Error: "Company Tax ID (RUC) is missing"

**Causa**: Company no tiene RUC configurado

**Solución**:
```
Company → Tax ID = "3604076-1"
```

### Error: "El cliente para operación B2B debe tener SIFEN Tipo Documento = 'RUC'"

**Causa**: Customer B2B sin tipo documento correcto

**Solución**:
```
Customer → Tax Information → SIFEN Tipo Documento = "1|RUC"
```

### Error: "La factura es una operación a Crédito pero no tiene plazo configurado"

**Causa**: Payment Schedule sin credit_days

**Solución**:
```
Payment Schedule → Credit Days = 30
```

### Error: "La Plantilla de Impuesto no tiene 'SIFEN Tipo IVA' configurado"

**Causa**: Item Tax Template sin sifen_tipo_iva

**Solución**:
```
Item Tax Template → Taxes → SIFEN Tipo IVA = "1|Gravado IVA"
```

---

## Referencias

- [Guía de Inicio Rápido](01_quick_start.md)
- [Validaciones](06_validations.md)
- [API SIFEN](07_sifen_api.md)
- [Solución de Problemas](09_troubleshooting.md)

---

**Última actualización:** 2026-03-28
