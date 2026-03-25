# Solución de Problemas (Troubleshooting)

Este documento describe errores comunes y sus soluciones.

---

## Errores de Validación

### 1. "Company Tax ID (RUC) is missing in Company {0}"

**Causa**: La empresa no tiene RUC configurado.

**Solución**:
```
1. Ir a Company List
2. Seleccionar la empresa
3. Tax Information → Tax ID = "123456-1"
4. Guardar
```

---

### 2. "El SIFEN Tipo Documento del cliente está vacío"

**Causa**: El customer no tiene `sifen_tipo_documento` configurado.

**Solución**:
```
1. Ir a Customer List
2. Seleccionar el customer
3. Tax Information → SIFEN Tipo Documento = "1|RUC"
4. Guardar
```

---

### 3. "El cliente para operación B2B debe tener SIFEN Tipo Documento = 'RUC'"

**Causa**: Customer B2B con tipo documento incorrecto.

**Solución**:
```
1. Verificar tipo de operación (debe ser B2B)
2. Customer → Tax Information → SIFEN Tipo Documento = "1|RUC"
3. Guardar
```

---

### 4. "La factura es una operación a Crédito pero no tiene plazo configurado"

**Causa**: Payment Schedule sin `credit_days` configurado.

**Solución**:
```
Opción A: Usar Payment Terms Template
1. Sales Invoice → Payment Terms Template = [Seleccionar plantilla con days]

Opción B: Configurar manualmente
1. Sales Invoice → Payment Schedule
2. Editar cada término
3. Credit Days = 30 (o los días correspondientes)
4. Guardar
```

---

### 5. "La Plantilla de Impuesto no tiene 'SIFEN Tipo IVA' configurado"

**Causa**: Item Tax Template sin `sifen_tipo_iva`.

**Solución**:
```
1. Ir a Item Tax Template List
2. Seleccionar la plantilla
3. Taxes → Editar fila
4. SIFEN Tipo IVA = "1|Gravado IVA"
5. Guardar
```

---

### 6. "La Plantilla de Impuesto tiene todos los impuestos con tasa 0%"

**Causa**: Item gravado con tax_rate = 0%.

**Solución**:
```
Si el item es gravado:
1. Item Tax Template → Taxes → Tax Rate = 10.0
2. Guardar

Si el item es exento:
1. Verificar que sifen_tipo_iva = "2" o "3"
2. Guardar
```

---

### 7. "La factura no tiene impuestos configurados en la tabla 'Sales Taxes and Charges'"

**Causa**: Tabla de impuestos vacía para customer de Paraguay.

**Solución**:
```
Opción A: Verificar Item Tax Template
1. Verificar que cada item tenga Item Tax Template
2. Verificar que el template tenga tax_rate > 0%

Opción B: Agregar impuesto manualmente
1. Sales Invoice → Taxes and Charges
2. Add Row
3. Account Head = [Cuenta de IVA]
4. Rate = 10.0
5. Guardar
```

---

## Errores de API

### 1. "Authentication failed. The API Key is invalid or expired"

**Causa**: API Key incorrecta o expirada en E-Invoice Setting.

**Solución**:
```
1. Ir a E-Invoice Setting
2. Verificar API Key
3. Contactar a SIFEN para nueva key si expiró
4. Actualizar API Key
5. Guardar
```

---

### 2. "Cannot connect to SIFEN API"

**Causa**: Problema de conexión o URL incorrecta.

**Solución**:
```
1. Verificar conexión a internet
2. E-Invoice Setting → API Endpoint
3. Verificar que la URL sea correcta
4. Probar acceso desde el servidor:
   curl -I {API_ENDPOINT}
5. Contactar administrador de red si hay firewall
```

---

### 3. "File not found in SIFEN API"

**Causa**: La factura no se procesó aún en SIFEN.

**Solución**:
```
1. Esperar unos minutos
2. Menú E-Invoice → Force Refresh Status
3. Verificar estado en SIFEN
4. Si persiste, contactar a SIFEN
```

---

## Errores de Datos

### 1. Número de Control no es único

**Causa**: Colisión de números de control (muy raro).

**Solución**:
```
El sistema reintenta automáticamente hasta 10 veces.
Si falla después de 10 intentos:
1. Reintentar guardar la factura
2. El sistema generará otro número automáticamente
```

---

### 2. Formato de Departamento incorrecto

**Causa**: Departamento no usa formato "código|descripción".

**Solución**:
```
1. Address → State
2. Usar botón 🔍 Buscar Departamento
3. Seleccionar departamento de la lista
4. El formato será "12|CENTRAL" automáticamente
5. Guardar
```

---

### 3. Customer sin Address completo

**Causa**: Address sin Departamento/Distrito/Ciudad.

**Solución**:
```
1. Ir a Address del customer
2. State → 🔍 Buscar Departamento → Seleccionar
3. County → 🔍 Buscar Distrito → Seleccionar
4. City → 🔍 Buscar Ciudad → Seleccionar
5. Guardar
```

---

## Errores de Submit/Validate

### 1. "You do not have permission to modify this invoice"

**Causa**: Usuario sin permisos de escritura.

**Solución**:
```
1. Verificar permisos del usuario:
   Settings → Users and Permissions → User
2. Agregar rol "Accounts User" o "Accounts Manager"
3. Guardar
```

---

### 2. "Cannot generate E-Invoice for a draft invoice"

**Causa**: Intentando enviar a SIFEN una factura en borrador.

**Solución**:
```
1. Validar la factura primero (Submit)
2. Luego usar Send to SIFEN
```

---

### 3. "E-Invoice already generated for this invoice"

**Causa**: La factura ya fue enviada a SIFEN.

**Solución**:
```
Opción A: Si necesita regenerar (solo Administrator)
1. Menú E-Invoice → Regenerate and Send

Opción B: Si solo quiere verificar estado
1. Menú E-Invoice → Check Local Status
```

---

## Problemas de Performance

### 1. Validación lenta

**Causa**: Muchos items o validaciones complejas.

**Solución**:
```
1. Verificar número de items (si > 100, considerar dividir factura)
2. Verificar índices en DB:
   bench --site development.localhost console
   
   from frappe.db import sql
   sql("SHOW INDEX FROM `tabSales Invoice` WHERE Key_name = 'idx_custom_numero_control'")
3. Si no existe el índice, reinstalar el módulo
```

---

### 2. Timeout en API

**Causa**: API SIFEN lenta o timeout muy corto.

**Solución**:
```
1. E-Invoice Setting → Request Timeout
2. Aumentar a 60 segundos
3. Guardar
4. Reintentar envío
```

---

## Problemas con Botones

### 1. Botón "Generar E-Invoice" no aparece

**Causa**: Factura no está validada.

**Solución**:
```
1. Validar la factura (Submit)
2. El botón aparecerá en el menú E-Invoice
```

---

### 2. Botón "Regenerate and Send" no aparece

**Causa**: Solo visible para Administrator.

**Solución**:
```
1. Iniciar sesión como Administrator
2. El botón será visible
```

---

### 3. Botones "Download XML/KUDE" no aparecen

**Causa**: Factura no tiene `custom_sifen_factura_id`.

**Solución**:
```
1. Enviar la factura a SIFEN primero
2. Después de la respuesta exitosa, los botones aparecerán
```

---

## Comandos Útiles

### Ver Logs de E-Invoice

```bash
# En bench console
bench --site development.localhost console

from frappe.utils import get_datetime
from_date = get_datetime().add_days(-1)

logs = frappe.get_all("Error Log", 
                     filters={"creation": [">=", from_date],
                              "method": ["like", "%E-Invoice%"]},
                     fields=["name", "method", "error", "creation"],
                     order_by="creation desc",
                     limit=20)

for log in logs:
    print(f"\n{log.creation}")
    print(f"Method: {log.method}")
    print(f"Error: {log.error[:200]}")
```

---

### Reinstalar Módulo

```bash
# Desinstalar
bench uninstall-app einvoice --yes

# Limpiar cache
bench clear-cache

# Instalar nuevamente
bench install-app einvoice

# Migrar DB
bench migrate
```

---

### Verificar Custom Fields

```bash
bench --site development.localhost console

# Verificar campos en Customer
fields = frappe.get_all("Custom Field", 
                       filters={"dt": "Customer", "module": "E-Invoice"},
                       fields=["fieldname", "label"])

for field in fields:
    print(f"{field.fieldname}: {field.label}")
```

---

## Contactar Soporte

Si ningún problema anterior se ajusta a tu caso:

1. **Recopilar información**:
   - Mensaje de error completo
   - Pasos para reproducir
   - Versión de ERPNext
   - Logs de error

2. **Verificar logs**:
   ```
   Menu → Settings → Error Log
   ```

3. **Contactar al equipo de desarrollo** con la información recopilada.

---

## Referencias

- [Validaciones](06_validations.md)
- [Flujo de Trabajo](08_workflow.md)
- [Referencia Técnica](10_technical_reference.md)

---

**Última actualización:** 2026-03-25
