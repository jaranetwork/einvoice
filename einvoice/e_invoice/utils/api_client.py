import frappe
import json
import requests
import re
from frappe import _
from frappe.utils import now_datetime, escape_html

@frappe.whitelist()
def download_sifen_file(factura_id, file_type, invoice_name=None):
    """
    Download XML or KUDE file from SIFEN API directly using factura_id.
    This function replaces the E-Invoice Record based download.
    
    Args:
        factura_id: SIFEN factura ID (e.g., "69bd8de9e6027b0a33a02c1b")
        file_type: 'xml' or 'kude'
        invoice_name: Sales Invoice name for filename (optional, e.g., "ACC-SINV-2026-00005")
    
    Returns:
        dict: {
            'file_content': str (base64 encoded),
            'filename': str,
            'content_type': str
        }
    """
    # Validate E-Invoice configuration exists
    try:
        settings = frappe.get_single("E-Invoice Setting")
    except Exception:
        frappe.throw(
            _("E-Invoice Setting not found. Please configure E-Invoice settings first."),
            title=_("Configuration Missing")
        )
    
    if not settings.enabled:
        frappe.throw(
            _("E-Invoice integration is not enabled. Please enable it in E-Invoice Setting."),
            title=_("E-Invoice Not Enabled")
        )
    
    if not settings.api_endpoint:
        frappe.throw(
            _("API Endpoint is not configured in E-Invoice Setting.<br><br>"
              "Please go to E-Invoice Setting and configure the API Endpoint."),
            title=_("API Endpoint Missing")
        )
    
    if not settings.api_key:
        frappe.throw(
            _("API Key is not configured in E-Invoice Setting.<br><br>"
              "Please go to E-Invoice Setting and configure the API Key."),
            title=_("API Key Missing")
        )
    
    if not factura_id:
        frappe.throw(_("Factura ID is required"))
    
    # Build API URL based on file type
    base_url = settings.api_endpoint.rstrip('/')
    
    if file_type == 'xml':
        # XML download endpoint: GET {BASE_URL}/api/invoices/{id}/download-xml
        url = f"{base_url}/api/invoices/{factura_id}/download-xml"
        # Use invoice_name for filename if provided, otherwise use factura_id
        filename = f"{invoice_name or factura_id}.xml"
        content_type = "application/xml"
    elif file_type == 'kude':
        # KUDE download endpoint: GET {BASE_URL}/api/invoices/{id}/download-pdf
        url = f"{base_url}/api/invoices/{factura_id}/download-pdf"
        # Use invoice_name for filename if provided, otherwise use factura_id
        filename = f"{invoice_name or factura_id}_KUDE.pdf"
        content_type = "application/pdf"
    else:
        frappe.throw(_("Invalid file type. Must be 'xml' or 'kude'"))
    
    # Make API request with authentication
    headers = {
        "Authorization": f"Bearer {settings.api_key}",
        "Accept": content_type
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        
        # Check response status
        if response.status_code == 200:
            # Return file content as base64
            import base64
            file_content = base64.b64encode(response.content).decode('utf-8')
            
            return {
                "file_content": file_content,
                "filename": filename,
                "content_type": content_type
            }
        elif response.status_code == 401:
            frappe.throw(
                _("Authentication failed. The API Key configured in E-Invoice Setting is invalid or expired.<br><br>"
                  "Please verify your API Key in E-Invoice Setting."),
                title=_("Authentication Error")
            )
        elif response.status_code == 403:
            frappe.throw(
                _("Access denied. Your API Key does not have permission to download this file.<br><br>"
                  "HTTP Status: {0}").format(response.status_code),
                title=_("Access Denied")
            )
        elif response.status_code == 404:
            frappe.throw(
                _("File not found in SIFEN API.<br><br>"
                  "The invoice may not be processed yet or the Factura ID is incorrect.<br><br>"
                  "Factura ID: {0}").format(factura_id),
                title=_("File Not Found")
            )
        else:
            # Try to parse error message from API
            try:
                error_data = response.json()
                error_message = error_data.get('message', f"HTTP {response.status_code}")
            except:
                error_message = f"HTTP {response.status_code}: {response.text[:200]}"
            
            frappe.throw(_("Failed to download file: {0}").format(error_message))
    
    except requests.exceptions.Timeout:
        frappe.throw(_("Request timeout. The SIFEN API took too long to respond. Please try again."))
    except requests.exceptions.ConnectionError:
        frappe.throw(
            _("Cannot connect to SIFEN API.<br><br>"
              "Please check:<br>"
              "1. Your internet connection<br>"
              "2. API Endpoint URL is correct<br>"
              "3. SIFEN API is available<br><br>"
              "API Endpoint: {0}").format(base_url))
    except requests.exceptions.RequestException as e:
        frappe.throw(_("Network error: {0}").format(str(e)))
    except Exception as e:
        frappe.throw(_("Error downloading file: {0}").format(str(e)))


def clean_html(text):
    """
    Remove HTML tags from text.
    
    Args:
        text: String that may contain HTML tags
    
    Returns:
        str: Clean text without HTML tags
    """
    if not text:
        return ""
    
    # Remove HTML tags using regex
    clean = re.sub(r'<[^>]+>', '', text)
    
    # Remove extra whitespace and newlines
    clean = ' '.join(clean.split())
    
    return clean.strip()


def get_einvoice_settings():
    """Get E-Invoice settings"""
    return frappe.get_single("E-Invoice Setting")

def get_base_url():
    """Get the base URL for the SIFEN API"""
    settings = get_einvoice_settings()
    # Remove trailing slash if present
    base_url = settings.api_endpoint.rstrip('/') if settings.api_endpoint else ""
    return base_url

def get_auth_headers():
    """Get authentication headers for API requests"""
    settings = get_einvoice_settings()
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.api_key}"
    }

def send_invoice_to_external_api(sales_invoice):
    """
    Send invoice data to external Paraguayan SIFEN API.
    Endpoint: POST {BASE_URL}/api/facturar/crear

    Expected API response format:
    {
        "success": true,
        "message": "Factura encolada para procesamiento asíncrono",
        "data": {
            "facturaId": "65f1234567890abcdef12345",
            "correlativo": "001-001-0000060",
            "estado": "encolado",
            "cdc": "ABC123456789",
            "jobId": "factura-65f1234567890abcdef12345",
            "xmlLink": "...",
            "kudeLink": "..."
        }
    }
    """

    settings = get_einvoice_settings()

    if not settings.enabled:
        return {"success": False, "message": "E-Invoice integration is not enabled"}

    # Prepare invoice data in SIFEN format
    invoice_data = prepare_invoice_data(sales_invoice)

    # Build URL for creating invoice
    base_url = get_base_url()
    url = f"{base_url}/api/facturar/crear"

    # Send to external API
    headers = get_auth_headers()

    try:
        response = requests.post(
            url,
            json=invoice_data,
            headers=headers,
            timeout=settings.request_timeout or 30
        )

        # Parse response JSON first
        try:
            result = response.json()
        except json.JSONDecodeError:
            return {
                "success": False,
                "message": f"Invalid JSON response from API: {response.text[:200]}"
            }

        # Check if response has success field and it's true
        if result.get("success") is True:
            # Process successful response
            message = result.get("message", "")
            data = result.get("data", {})

            # Extract data from response
            factura_id = data.get("facturaId", "")
            correlativo = data.get("correlativo", "")
            estado = data.get("estado", "")
            cdc = data.get("cdc")
            job_id = data.get("jobId", "")
            xml_link = data.get("xmlLink", "")
            kude_link = data.get("kudeLink", "")
            
            # Extract URLs from nested urls object
            urls = data.get("urls", {})
            url_estado = urls.get("estado", "")
            url_consulta = urls.get("consulta", "")
            
            # Map API estado to E-Invoice Record status options
            estado_for_status = map_estado_to_status(estado)

            # Store factura_id in sales invoice for future operations
            frappe.db.set_value(
                "Sales Invoice",
                sales_invoice.name,
                "custom_sifen_factura_id",
                factura_id
            )

            # Update sales invoice with all e-invoice info (no separate E-Invoice Record)
            frappe.db.set_value(
                "Sales Invoice",
                sales_invoice.name,
                {
                    "custom_einvoice_json": json.dumps(invoice_data, indent=2),
                    "custom_einvoice_generated": 1,
                    "custom_einvoice_generated_date": now_datetime(),
                    "custom_sifen_factura_id": factura_id,
                    "custom_sifen_correlativo": correlativo,
                    "custom_sifen_estado": estado,
                    "custom_sifen_cdc": cdc,
                    "custom_sifen_xml_link": xml_link,
                    "custom_sifen_kude_link": kude_link
                }
            )

            frappe.db.commit()

            # Format a user-friendly message
            formatted_message = format_success_message(data, message)

            return {
                "success": True,
                "message": formatted_message,
                "data": data
            }
        else:
            # API returned success: false or no success field
            error_message = result.get("message", "Unknown error")
            error_detail = result.get("error", "")
            full_error = f"{error_message} {error_detail}".strip()
            
            frappe.log_error(
                f"E-Invoice API Error for Invoice {sales_invoice.name}: {full_error[:100]}",
                "E-Invoice API Error"
            )
            
            return {
                "success": False,
                "message": full_error or f"API returned failure (HTTP {response.status_code})"
            }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "message": "Request timeout while connecting to external API"
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "message": f"Request error: {str(e)[:100]}"
        }
    except Exception as e:
        error_msg = str(e)[:100]
        frappe.log_error(f"E-Invoice API Error: {error_msg}", "E-Invoice API Error")
        return {
            "success": False,
            "message": f"Internal error: {error_msg}"
        }


def format_success_message(data, base_message=""):
    """
    Format the API response data into a user-friendly message.
    
    Args:
        data: Dictionary containing facturaId, correlativo, estado, cdc, xmlLink, kudeLink
        base_message: Optional base message from API
    
    Returns:
        Formatted HTML string
    """
    # Build a nice formatted message using HTML table
    html_lines = []
    html_lines.append('<div style="padding: 15px; background: #f8f9fa; border-radius: 5px; border: 1px solid #dee2e6; font-family: -apple-system, BlinkMacSystemFont, sans-serif;">')
    html_lines.append('<h4 style="margin-top: 0; margin-bottom: 15px; color: #28a745; font-size: 16px;">✓ E-Invoice Generated Successfully</h4>')
    
    if base_message:
        html_lines.append(f'<p style="margin: 10px 0; color: #6c757d; font-size: 14px;"><strong>Message:</strong> {escape_html(base_message)}</p>')
    
    html_lines.append('<table style="width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px;">')
    
    if data.get("facturaId"):
        html_lines.append(
            '<tr><td style="padding: 10px 8px; border-bottom: 1px solid #dee2e6; font-weight: 600; width: 120px; color: #495057;">Factura ID:</td>'
            f'<td style="padding: 10px 8px; border-bottom: 1px solid #dee2e6; color: #212529;">{escape_html(str(data.get("facturaId")))}</td></tr>'
        )
    
    if data.get("correlativo"):
        html_lines.append(
            '<tr><td style="padding: 10px 8px; border-bottom: 1px solid #dee2e6; font-weight: 600; color: #495057;">Correlativo:</td>'
            f'<td style="padding: 10px 8px; border-bottom: 1px solid #dee2e6; color: #212529;">{escape_html(str(data.get("correlativo")))}</td></tr>'
        )
    
    if data.get("estado"):
        status_color = "#28a745" if str(data.get("estado")).lower() in ["aprobado", "aceptado", "encolado"] else "#ffc107"
        html_lines.append(
            '<tr><td style="padding: 10px 8px; border-bottom: 1px solid #dee2e6; font-weight: 600; color: #495057;">Estado:</td>'
            f'<td style="padding: 10px 8px; border-bottom: 1px solid #dee2e6; color: {status_color}; font-weight: 700;">{escape_html(str(data.get("estado")))}</td></tr>'
        )
    
    if data.get("cdc"):
        html_lines.append(
            '<tr><td style="padding: 10px 8px; border-bottom: 1px solid #dee2e6; font-weight: 600; color: #495057;">CDC:</td>'
            f'<td style="padding: 10px 8px; border-bottom: 1px solid #dee2e6; color: #212529;">{escape_html(str(data.get("cdc")))}</td></tr>'
        )
    
    # Add download links if available
    if data.get("xmlLink") or data.get("kudeLink"):
        html_lines.append('<tr><td style="padding: 10px 8px; border-bottom: 1px solid #dee2e6; font-weight: 600; color: #495057;">Downloads:</td>')
        html_lines.append('<td style="padding: 10px 8px; border-bottom: 1px solid #dee2e6; color: #212529;">')
        links = []
        if data.get("xmlLink"):
            links.append(f'<a href="{escape_html(data.get("xmlLink"))}" target="_blank" style="color: #007bff; text-decoration: none;">XML</a>')
        if data.get("kudeLink"):
            links.append(f'<a href="{escape_html(data.get("kudeLink"))}" target="_blank" style="color: #007bff; text-decoration: none;">KUDE (PDF)</a>')
        html_lines.append(' | '.join(links))
        html_lines.append('</td></tr>')
    
    html_lines.append('</table></div>')
    
    return ''.join(html_lines)

def parse_naming_series(series, invoice_name=None):
    """
    Parse ERPNext naming series to extract establishment, point and number.
    Example: 'SINV-25-00001' or '001-001-0000003' or 'ACC-SINV-2026-00004'
    Returns: (establecimiento, punto, numero)

    Simple approach: extract everything after the last hyphen as the number.
    If invoice_name is provided, use it directly (ignores series with placeholders).
    """
    # If invoice_name is provided, use it directly (it has the actual number)
    if invoice_name:
        last_hyphen_idx = invoice_name.rfind('-')
        
        if last_hyphen_idx != -1 and last_hyphen_idx < len(invoice_name) - 1:
            # Extract everything after last hyphen from invoice_name
            numero = invoice_name[last_hyphen_idx + 1:]
            
            # Take last 8 digits if too long (SIFEN max)
            if len(numero) > 8:
                numero = numero[-8:]
            
            # Extract est and punto from remaining parts
            remaining = invoice_name[:last_hyphen_idx]
            parts = remaining.split('-')
            
            if len(parts) >= 2:
                est_raw = parts[-2]
                punto_raw = parts[-1]
                
                est = est_raw.zfill(3)[-3:] if est_raw.isdigit() else "001"
                punto = punto_raw.zfill(3)[-3:] if punto_raw.isdigit() else "001"
                
                return est, punto, numero
            
            # Only one part before number
            return "001", "001", numero
    
    # Fallback: use series if invoice_name not available
    if not series:
        return "001", "001", "0000000"

    # Simple approach: find last hyphen and extract everything after it
    last_hyphen_idx = series.rfind('-')

    if last_hyphen_idx != -1 and last_hyphen_idx < len(series) - 1:
        # Extract everything after last hyphen
        numero = series[last_hyphen_idx + 1:]

        # Take last 8 digits if too long (SIFEN max)
        if len(numero) > 8:
            numero = numero[-8:]

        # Try to find establishment and point from earlier parts
        remaining = series[:last_hyphen_idx]
        parts = remaining.split('-')

        if len(parts) >= 2:
            est_raw = parts[-2]
            punto_raw = parts[-1]

            # Validate establishment is numeric (max 3 digits)
            if est_raw.isdigit():
                est = est_raw.zfill(3)[-3:]
            else:
                est = "001"

            # Validate point is numeric (max 3 digits)
            if punto_raw.isdigit():
                punto = punto_raw.zfill(3)[-3:]
            else:
                punto = "001"

            return est, punto, numero

        # Only one part before number
        return "001", "001", numero

    # No hyphen found, use entire series as number
    return "001", "001", series[-8:] if len(series) > 8 else series


def get_paraguay_location_codes(state, city, country):
    """
    Get Paraguay department and district codes from address data.
    Returns dictionary with department and district codes and descriptions.

    City format in DB: "5940|LIMPIO (MUNICIPIO)" where 5940 is the city code.
    District codes are typically the same as city codes for the main city.
    """
    result = {
        "departamento": None,
        "departamentoDescripcion": "",
        "distrito": None,
        "distritoDescripcion": "",
        "ciudad": None,
        "ciudadDescripcion": "",
        "pais": None,
        "paisDescripcion": ""
    }

    if country:
        result["pais"] = "PRY"
        result["paisDescripcion"] = country

    if state:
        state_clean = state
        if "|" in state:
            state_clean = state.split("|", 1)[1]
        
        state_upper = state_clean.upper()
        dept_mapping = {
            "ALTO PARANA": (11, "ALTO PARANA"),
            "ASUNCION": (1, "ASUNCION"),
            "CENTRAL": (12, "CENTRAL"),
            "CORDILLERA": (4, "CORDILLERA"),
            "GUAIRA": (5, "GUAIRA"),
            "CAAGUAZU": (6, "CAAGUAZU"),
            "CAAZAPA": (7, "CAAZAPA"),
            "ITAPUA": (8, "ITAPUA"),
            "MISIONES": (9, "MISIONES"),
            "PARAGUARI": (10, "PARAGUARI"),
            "ALTO PARAGUAY": (12, "ALTO PARAGUAY"),
            "BOQUERON": (13, "BOQUERON"),
            "AMAMBAY": (14, "AMAMBAY"),
            "CANINDEYU": (15, "CANINDEYU"),
            "PRESIDENTE HAYES": (16, "PRESIDENTE HAYES"),
            "NEEMBUCU": (17, "NEEMBUCU")
        }
        if state_upper in dept_mapping:
            result["departamento"] = dept_mapping[state_upper][0]
            result["departamentoDescripcion"] = dept_mapping[state_upper][1]

    if city:
        city_code = ""
        city_clean = city
        if "|" in city:
            parts = city.split("|", 1)
            city_code = parts[0]
            city_clean = parts[1]
        
        result["ciudadDescripcion"] = city_clean
        
        if city_code:
            result["ciudad"] = int(city_code)
            result["distrito"] = int(city_code)
            result["distritoDescripcion"] = city_clean.split(" ")[0]

    return result


def get_company_and_pos_codes(sales_invoice):
    """
    Get establishment and expedition point codes.

    Priority for expedition point code:
    1. POS Profile (if invoice comes from POS) - overrides company default
    2. Company default (codigo_punto_expedicion_default)
    3. Parse from naming_series (last resort)

    - Establishment Code: From Company (HQ or branch)
    - Expedition Point Code: From POS Profile or Company default

    Returns: (establecimiento, punto)
    """
    establecimiento = "001"
    punto = "001"

    # ============================================
    # Get Codes from Company (both fields)
    # ============================================
    if sales_invoice.company:
        try:
            company_doc = frappe.get_doc("Company", sales_invoice.company)

            # Get establishment code from Company
            if hasattr(company_doc, 'codigo_establecimiento') and company_doc.codigo_establecimiento:
                establecimiento = company_doc.codigo_establecimiento
                # Validate establishment code has max 3 digits
                if len(establecimiento) > 3:
                    frappe.throw(
                        _("El Código de Establecimiento no puede superar 3 dígitos. Valor actual: {0}").format(establecimiento),
                        title=_("Error en Código de Establecimiento")
                    )

            # Get default expedition point from Company
            if hasattr(company_doc, 'codigo_punto_expedicion_default') and company_doc.codigo_punto_expedicion_default:
                punto = company_doc.codigo_punto_expedicion_default
                # Validate expedition point code has max 3 digits
                if len(punto) > 3:
                    frappe.throw(
                        _("El Código de Punto de Expedición no puede superar 3 dígitos. Valor actual: {0}").format(punto),
                        title=_("Error en Punto de Expedición")
                    )

        except Exception:
            # Fallback to default if Company lookup fails
            pass
    
    # ============================================
    # Override expedition point from POS Profile (if applicable)
    # ============================================
    pos_profile = None
    
    # Check if invoice has a direct POS Profile reference
    if hasattr(sales_invoice, 'pos_profile') and sales_invoice.pos_profile:
        pos_profile = sales_invoice.pos_profile
    else:
        # Try to find POS Profile from POS Invoice link if exists
        pos_invoice = frappe.db.get_value(
            "POS Invoice",
            {"consolidated_invoice": sales_invoice.name},
            "pos_profile"
        )
        if pos_invoice:
            pos_profile = pos_invoice
    
    # If POS Profile found, override expedition point code
    if pos_profile:
        try:
            pos_doc = frappe.get_doc("POS Profile", pos_profile)
            
            # Get custom field from POS Profile (overrides company default)
            if hasattr(pos_doc, 'codigo_punto_expedicion') and pos_doc.codigo_punto_expedicion:
                punto = pos_doc.codigo_punto_expedicion
                
        except Exception:
            # Keep company default if POS Profile lookup fails
            pass
    
    # ============================================
    # Fallback: Parse from naming_series
    # ============================================
    # Only use parsed values if codes are still at defaults
    if establecimiento == "001" and punto == "001":
        parsed_est, parsed_punto, _ = parse_naming_series(sales_invoice.naming_series, sales_invoice.name)
        # Only use parsed values if they differ from default
        if parsed_est != "001" or parsed_punto != "001":
            establecimiento = parsed_est
            punto = parsed_punto
    
    return establecimiento, punto


def generar_numero_control(company=None):
    """
    Generar código de seguridad aleatorio de 9 dígitos único para SIFEN.
    
    Rango: 000000001 a 999999999
    La unicidad es por compañía (RUC), no global.
    Usa índice único en DB para verificación rápida O(1).
    
    Args:
        company: Company name para filtrar unicidad (opcional)
    
    Returns:
        str: Código de 9 dígitos único (con ceros a la izquierda)
    
    Raises:
        frappe.ValidationError: Si no puede generar código único después de 10 intentos
    """
    import random
    
    max_intentos = 10
    
    for intento in range(max_intentos):
        # Generar número aleatorio entre 1 y 999999999
        numero = random.randint(1, 999999999)
        # Formatear a 9 dígitos con ceros a la izquierda
        codigo = str(numero).zfill(9)
        
        # Verificar si ya existe en otra factura activa de la MISMA compañía
        filters = {
            "custom_numero_control": codigo,
            "docstatus": ("!=", 2)  # Excluir canceladas
        }
        
        # Si hay compañía, filtrar solo dentro de esa compañía
        if company:
            filters["company"] = company
        
        existe = frappe.db.exists("Sales Invoice", filters)
        
        if not existe:
            return codigo
    
    # Si llega aquí, hubo muchas colisiones (muy improbable)
    frappe.throw(_(
        "No se pudo generar código único después de {0} intentos. "
        "Reintente en unos segundos."
    ).format(max_intentos))


def asignar_numero_control(doc, method=None):
    """
    Asignar número de control único a la factura.

    Se ejecuta en el evento validate de Sales Invoice.
    Solo genera un nuevo código si la factura no tiene uno asignado.
    La unicidad es por compañía, no global.

    Args:
        doc: Sales Invoice document
        method: Event method name (unused)
    """
    # Solo asignar si no tiene número de control
    if not doc.custom_numero_control:
        doc.custom_numero_control = generar_numero_control(doc.company)


def validar_campos_sifen(doc, method=None):
    """
    Validar campos requeridos por SIFEN antes de enviar factura.

    Se ejecuta en el evento validate de Sales Invoice.
    Valida todos los campos requeridos según el tipo de operación (B2B, B2C, B2G, B2F).

    Args:
        doc: Sales Invoice document
        method: Event method name (unused)

    Raises:
        frappe.ValidationError: Si faltan campos requeridos
    """
    errors = []

    # ============================================
    # Validar Configuración E-Invoice
    # ============================================
    try:
        settings = frappe.get_single("E-Invoice Setting")
        if not settings.enabled:
            errors.append(
                _("La integración E-Invoice no está habilitada.<br><br>"
                  "Por favor, habilítela en E-Invoice Setting.")
            )
    except Exception:
        errors.append(
            _("E-Invoice Setting no está configurado correctamente.")
        )

    # ============================================
    # Validar Datos de la Empresa
    # ============================================
    company = frappe.get_doc("Company", doc.company)

    if not company.tax_id:
        errors.append(
            _("El RUC de la empresa está vacío en Company {0}.<br><br>"
              "El RUC es obligatorio para emitir facturas electrónicas.").format(doc.company)
        )

    if not hasattr(company, 'codigo_establecimiento') or not company.codigo_establecimiento:
        errors.append(
            _("El Código de Establecimiento está vacío en Company {0}.<br><br>"
              "Este campo es obligatorio para SIFEN (máximo 3 dígitos).").format(doc.company)
        )
    elif len(company.codigo_establecimiento) > 3:
        errors.append(
            _("El Código de Establecimiento no puede superar 3 dígitos.<br><br>"
              "Valor actual: {0}").format(company.codigo_establecimiento)
        )

    if not hasattr(company, 'numero_timbrado') or not company.numero_timbrado:
        errors.append(
            _("El Número de Timbrado está vacío en Company {0}.<br><br>"
              "Este campo es obligatorio para SIFEN.").format(doc.company)
        )

    if not hasattr(company, 'fecha_timbrado') or not company.fecha_timbrado:
        errors.append(
            _("La Fecha de Timbrado está vacía en Company {0}.<br><br>"
              "Este campo es obligatorio para SIFEN.").format(doc.company)
        )

    if not hasattr(company, 'tipo_regimen') or not company.tipo_regimen:
        errors.append(
            _("El Tipo de Régimen está vacío en Company {0}.<br><br>"
              "Este campo es obligatorio para SIFEN (1-8).").format(doc.company)
        )

    if not hasattr(company, 'tipo_contribuyente') or not company.tipo_contribuyente:
        errors.append(
            _("El Tipo de Contribuyente está vacío en Company {0}.<br><br>"
              "Este campo es obligatorio para SIFEN (1=Persona Física, 2=Persona Jurídica).").format(doc.company)
        )

    # Validar Actividades Económicas
    if not hasattr(company, 'actividades_economicas') or not company.actividades_economicas:
        errors.append(
            _("No hay Actividades Económicas configuradas en Company {0}.<br><br>"
              "Por favor, agregue al menos una actividad económica.").format(doc.company)
        )
    elif len(company.actividades_economicas) == 0:
        errors.append(
            _("Al menos una Actividad Económica es requerida en Company {0}.").format(doc.company)
        )
    else:
        for idx, actividad in enumerate(company.actividades_economicas):
            if not actividad.codigo_actividad:
                errors.append(
                    _("La Actividad Económica #{0} no tiene código.<br><br>"
                      "Por favor, complete el campo 'Código de Actividad'.").format(idx + 1)
                )
            if not actividad.descripcion_actividad:
                errors.append(
                    _("La Actividad Económica #{0} no tiene descripción.<br><br>"
                      "Por favor, complete el campo 'Descripción de Actividad'.").format(idx + 1)
                )

    # Validar Persona Responsable SIFEN
    if not hasattr(company, 'sifen_responsable_tipo_documento') or not company.sifen_responsable_tipo_documento:
        errors.append(
            _("El Tipo de Documento del Responsable SIFEN está vacío en Company {0}.<br><br>"
              "Este campo es obligatorio para la firma electrónica.").format(doc.company)
        )

    if not hasattr(company, 'sifen_respons_numero_documento') or not company.sifen_respons_numero_documento:
        errors.append(
            _("El Número de Documento del Responsable SIFEN está vacío en Company {0}.<br><br>"
              "Este campo es obligatorio para la firma electrónica.").format(doc.company)
        )

    if not hasattr(company, 'sifen_responsable_nombre') or not company.sifen_responsable_nombre:
        errors.append(
            _("El Nombre del Responsable SIFEN está vacío en Company {0}.<br><br>"
              "Este campo es obligatorio para la firma electrónica.").format(doc.company)
        )

    if not hasattr(company, 'sifen_responsable_cargo') or not company.sifen_responsable_cargo:
        errors.append(
            _("El Cargo del Responsable SIFEN está vacío en Company {0}.<br><br>"
              "Este campo es obligatorio para la firma electrónica.").format(doc.company)
        )

    # ============================================
    # Validar Datos del Cliente
    # ============================================
    if not doc.customer:
        errors.append(_("El cliente es obligatorio."))

    customer_data = None
    customer_country = ""
    customer_tax_id = ""
    customer_type = ""
    customer_group = ""
    customer_contribuyente = False
    customer_sifen_tipo_documento = ""
    customer_sifen_tipo_impuesto = ""

    if doc.customer:
        customer_data = frappe.db.get_value(
            "Customer",
            doc.customer,
            ["customer_type", "customer_group", "tax_id", "sifen_contribuyente", "sifen_tipo_documento", "sifen_tipo_impuesto"],
            as_dict=True
        )
        if customer_data:
            customer_type = customer_data.customer_type or ""
            customer_group = customer_data.customer_group or ""
            customer_tax_id = customer_data.tax_id or ""
            customer_contribuyente = bool(customer_data.sifen_contribuyente) if customer_data.sifen_contribuyente else False
            customer_sifen_tipo_documento = customer_data.sifen_tipo_documento or ""
            customer_sifen_tipo_impuesto = customer_data.sifen_tipo_impuesto or ""

        # Obtener país del address del cliente
        if doc.customer_address:
            address_data = frappe.db.get_value(
                "Address",
                doc.customer_address,
                ["country", "state", "county", "city"],
                as_dict=True
            )
            if address_data:
                customer_country = address_data.country or ""

                # Validar formato de departamento (state)
                if address_data.state:
                    state_value = address_data.state.strip()
                    if state_value and not state_value.split('|')[0].isdigit():
                        errors.append(
                            _("El Departamento (State) del address debe estar en formato '1|CAPITAL' o '1'.<br><br>"
                              "Address: {0}<br>"
                              "Valor actual: {1}<br><br>"
                              "Use el botón 🔍 Buscar Departamento para seleccionar un departamento válido.").format(
                                doc.customer_address,
                                address_data.state
                            )
                        )
        else:
            # Fallback: intentar obtener el país por defecto del Customer
            # (si no hay address seleccionado, usar el país del registro del cliente)
            try:
                customer_default_country = frappe.db.get_value("Customer", doc.customer, "country")
                if customer_default_country:
                    customer_country = customer_default_country
            except Exception:
                pass

    # Determinar tipoOperacion para validación
    tipo_operacion = None

    if customer_data:
        if customer_type == "Company":
            customer_group_lower = customer_group.lower() if customer_group else ""
            if "gubernamental" in customer_group_lower or "government" in customer_group_lower:
                tipo_operacion = 3  # B2G
            else:
                tipo_operacion = 1  # B2B
        elif customer_type == "Individual":
            if customer_country and customer_country != "Paraguay":
                tipo_operacion = 4  # B2F
            else:
                tipo_operacion = 2  # B2C

        # Override para clientes sin RUC
        if not customer_tax_id:
            if customer_country and customer_country != "Paraguay":
                tipo_operacion = 4  # B2F
            else:
                tipo_operacion = 2  # B2C

    if tipo_operacion is None:
        errors.append(
            _("No se pudo determinar el tipoOperacion (tipo de operación) para el cliente {0}.<br><br>"
              "Datos del cliente:<br>"
              "- customer_type: {1}<br>"
              "- customer_group: {2}<br>"
              "- country: {3}<br>"
              "- tax_id: {4}<br><br>"
              "Por favor, verifique que los datos del cliente estén completos.").format(
                doc.customer,
                customer_type or "N/A",
                customer_group or "N/A",
                customer_country or "N/A",
                customer_tax_id or "N/A"
            )
        )
    else:
        # Validar según tipoOperacion
        if tipo_operacion == 4:  # B2F - Extranjero
            # Validar que el país NO sea Paraguay
            if customer_country == "Paraguay":
                errors.append(
                    _("La operación B2F (Extranjero) requiere un país diferente a Paraguay.<br><br>"
                      "País actual: {0}<br><br>"
                      "Por favor, actualice el address del cliente para tener un país diferente a Paraguay.").format(
                        customer_country or "N/A"
                    )
                )

            # Validar que el cliente NO sea contribuyente
            if customer_contribuyente:
                errors.append(
                    _("La operación B2F (Extranjero) requiere que el cliente sea 'No Contribuyente'.<br><br>"
                      "Actual: Es contribuyente = Yes<br><br>"
                      "Por favor, desmarque 'Es contribuyente?' en la sección de impuestos del cliente.")
                )
            
            # Validar SIFEN Tipo Documento para B2F (debe ser 3=Pasaporte o 4=Otro)
            if customer_sifen_tipo_documento:
                # Extraer el código numérico del formato almacenado (ej: "3|Pasaporte" → "3")
                tipo_documento_codigo = str(customer_sifen_tipo_documento).strip()
                if '|' in tipo_documento_codigo:
                    tipo_documento_codigo = tipo_documento_codigo.split('|')[0].strip()
                
                if tipo_documento_codigo not in ["3", "4"]:
                    errors.append(
                        _("El cliente extranjero (B2F) debe tener SIFEN Tipo Documento = 'Pasaporte' o 'Otro'.<br><br>"
                          "Cliente: {0}<br>"
                          "Tipo Documento Actual: {1}<br><br>"
                          "Por favor, actualice el campo 'SIFEN Tipo Documento' en el registro del cliente.").format(
                            doc.customer,
                            customer_sifen_tipo_documento
                        )
                    )

        else:  # B2B, B2C, B2G - Operaciones en Paraguay
            # Validar RUC del cliente para B2B y B2G
            if tipo_operacion in [1, 3] and not customer_tax_id:
                errors.append(
                    _("El RUC del cliente es obligatorio para operación {0}.<br><br>"
                      "Cliente: {1}<br>"
                      "tipoOperacion: {2} ({3})<br><br>"
                      "Por favor, establezca el RUC en el registro del cliente.").format(
                        "B2B" if tipo_operacion == 1 else "B2G",
                        doc.customer,
                        tipo_operacion,
                        "B2B" if tipo_operacion == 1 else "B2G"
                    )
                )
            
            # Validar SIFEN Tipo Documento para clientes en Paraguay
            if not customer_sifen_tipo_documento:
                errors.append(
                    _("El SIFEN Tipo Documento del cliente está vacío.<br><br>"
                      "Cliente: {0}<br><br>"
                      "Por favor, seleccione el tipo de documento en el campo 'SIFEN Tipo Documento' en el registro del cliente.<br><br>"
                      "Opciones:<br>"
                      "1 = RUC (para contribuyentes)<br>"
                      "2 = CI (Cédula de Identidad)<br>"
                      "3 = Pasaporte<br>"
                      "4 = Otro").format(doc.customer)
                )
            else:
                # Extraer el código numérico del formato almacenado (ej: "1|RUC" → "1")
                tipo_documento_codigo = str(customer_sifen_tipo_documento).strip()
                if '|' in tipo_documento_codigo:
                    tipo_documento_codigo = tipo_documento_codigo.split('|')[0].strip()
                
                if tipo_operacion in [1, 3] and tipo_documento_codigo != "1":
                    # B2B/B2G debe tener documento tipo 1 (RUC)
                    errors.append(
                        _("El cliente para operación {0} debe tener SIFEN Tipo Documento = 'RUC'.<br><br>"
                          "Cliente: {1}<br>"
                          "Tipo Documento Actual: {2}<br><br>"
                          "Por favor, actualice el campo 'SIFEN Tipo Documento' en el registro del cliente.").format(
                            "B2B" if tipo_operacion == 1 else "B2G",
                            doc.customer,
                            customer_sifen_tipo_documento
                        )
                    )
                elif tipo_operacion == 2 and tipo_documento_codigo not in ["1", "2"]:
                    # B2C puede tener RUC o CI
                    errors.append(
                        _("El cliente para operación B2C debe tener SIFEN Tipo Documento = 'RUC' o 'CI'.<br><br>"
                          "Cliente: {0}<br>"
                          "Tipo Documento Actual: {1}<br><br>"
                          "Por favor, actualice el campo 'SIFEN Tipo Documento' en el registro del cliente.").format(
                            doc.customer,
                            customer_sifen_tipo_documento
                        )
                    )

            # Validar SIFEN Tipo Impuesto para todos los clientes
            if not customer_sifen_tipo_impuesto:
                errors.append(
                    _("El SIFEN Tipo Impuesto del cliente está vacío.<br><br>"
                      "Cliente: {0}<br><br>"
                      "Por favor, seleccione el tipo de impuesto en el campo 'SIFEN Tipo Impuesto' en el registro del cliente.<br><br>"
                      "Opciones:<br>"
                      "1 = IVA (cliente local contribuyente)<br>"
                      "2 = ISC (productos con impuesto selectivo)<br>"
                      "3 = Renta (cliente extranjero B2F con RUC)<br>"
                      "4 = Ninguno (cliente extranjero sin RUC, consumidor final)<br>"
                      "5 = IVA - Renta (mixto)").format(doc.customer)
                )
            else:
                # Validar coherencia entre tipoOperacion y tipoImpuesto
                # Extraer el código numérico del formato almacenado (ej: "1|IVA" → "1")
                tipo_impuesto_codigo = str(customer_sifen_tipo_impuesto).strip()
                if '|' in tipo_impuesto_codigo:
                    tipo_impuesto_codigo = tipo_impuesto_codigo.split('|')[0].strip()
                
                if tipo_operacion in [1, 2, 3]:  # B2B, B2C, B2G - Paraguay
                    if tipo_impuesto_codigo in ["3", "4"]:
                        errors.append(
                            _("El SIFEN Tipo Impuesto no es coherente con el tipo de operación.<br><br>"
                              "Cliente: {0}<br>"
                              "tipoOperacion: {1} ({2})<br>"
                              "SIFEN Tipo Impuesto Actual: {3}<br><br>"
                              "Para operaciones en Paraguay (B2B/B2C/B2G), use:<br>"
                              "1 = IVA (cliente local contribuyente)<br>"
                              "2 = ISC (productos con impuesto selectivo)<br>"
                              "5 = IVA - Renta (mixto)").format(
                                doc.customer,
                                tipo_operacion,
                                "B2B" if tipo_operacion == 1 else "B2C" if tipo_operacion == 2 else "B2G",
                                customer_sifen_tipo_impuesto
                            )
                        )
                elif tipo_operacion == 4:  # B2F - Extranjero
                    if tipo_impuesto_codigo not in ["3", "4"]:
                        errors.append(
                            _("El SIFEN Tipo Impuesto no es coherente con el tipo de operación.<br><br>"
                              "Cliente: {0}<br>"
                              "tipoOperacion: {1} (B2F - Extranjero)<br>"
                              "SIFEN Tipo Impuesto Actual: {2}<br><br>"
                              "Para operaciones con extranjeros (B2F), use:<br>"
                              "3 = Renta (cliente extranjero con RUC)<br>"
                              "4 = Ninguno (cliente extranjero sin RUC)").format(
                                doc.customer,
                                tipo_operacion,
                                customer_sifen_tipo_impuesto
                            )
                        )

            # Validar address para B2B, B2C, B2G (solo addresses en Paraguay)
            if doc.customer_address:
                address = frappe.get_doc("Address", doc.customer_address)

                # Solo validar state/county/city si el país es Paraguay
                if address.country == "Paraguay":
                    # Validar departamento (state)
                    if not address.state:
                        errors.append(
                            _("El Departamento (State) es obligatorio en el address del cliente para tipoOperacion {0} (Paraguay).<br><br>"
                              "Address: {1}<br><br>"
                              "Por favor, seleccione un departamento paraguayo válido usando el botón 🔍 Buscar Departamento.").format(
                                tipo_operacion,
                                doc.customer_address
                            )
                        )

                    # Validar distrito (county)
                    if not address.county:
                        errors.append(
                            _("El Distrito (County) es obligatorio en el address del cliente para tipoOperacion {0} (Paraguay).<br><br>"
                              "Address: {1}<br><br>"
                              "Por favor, seleccione un distrito paraguayo válido.").format(
                                tipo_operacion,
                                doc.customer_address
                            )
                        )

                    # Validar ciudad (city)
                    if not address.city:
                        errors.append(
                            _("La Ciudad (City) es obligatoria en el address del cliente para tipoOperacion {0} (Paraguay).<br><br>"
                              "Address: {1}<br><br>"
                              "Por favor, seleccione una ciudad paraguaya válida.").format(
                                tipo_operacion,
                                doc.customer_address
                            )
                        )
                else:
                    # Address fuera de Paraguay - validar que el país esté configurado
                    if not address.country:
                        errors.append(
                            _("El país es obligatorio en el address del cliente para clientes extranjeros.<br><br>"
                              "Address: {1}<br><br>"
                              "Por favor, seleccione el país del cliente.").format(
                                tipo_operacion,
                                doc.customer_address
                            )
                        )

    # ============================================
    # Validar Items de la Factura
    # ============================================
    if not doc.items:
        errors.append(_("No hay items en la factura."))
    else:
        for idx, item in enumerate(doc.items):
            if not item.item_code:
                errors.append(_("El código del item es obligatorio para el item #{0}").format(idx + 1))
            if not item.rate:
                errors.append(_("El precio unitario es obligatorio para el item #{0} ({1})").format(idx + 1, item.item_code or "Desconocido"))
            if not item.qty:
                errors.append(_("La cantidad es obligatoria para el item #{0} ({1})").format(idx + 1, item.item_code or "Desconocido"))

            # Validar que el item tenga Item Tax Template configurado
            # Primero verifica en la factura, luego en el Item master
            has_tax_template = False
            tax_template_name = None
            
            # Verificar si el item en la factura tiene tax template
            if hasattr(item, 'item_tax_template') and item.item_tax_template:
                has_tax_template = True
                tax_template_name = item.item_tax_template
            else:
                # Verificar en el Item master
                try:
                    item_tax_template_master = frappe.db.get_value("Item", item.item_code, "item_tax_template")
                    if item_tax_template_master:
                        has_tax_template = True
                        tax_template_name = item_tax_template_master
                except Exception:
                    # El campo no existe en Item, solo verifica el de la factura
                    pass
            
            if not has_tax_template:
                errors.append(
                    _("El item #{0} ({1}) no tiene Plantilla de Impuesto (Item Tax Template) configurada.<br><br>"
                      "Por favor, configure la Plantilla de Impuesto en:<br>"
                      "1. El Item (Item master), o<br>"
                      "2. La línea del item en esta factura<br><br>"
                      "Este campo es necesario para determinar el ivaTipo (afectación al IVA).").format(
                        idx + 1,
                        item.item_code or "Desconocido"
                    )
                )
            else:
                # Validar que la Plantilla de Impuesto tenga al menos una línea de impuesto
                if tax_template_name:
                    try:
                        taxes = frappe.db.get_all(
                            "Item Tax Template Detail",
                            filters={"parent": tax_template_name},
                            fields=["sifen_tipo_iva", "tax_rate", "tax_type"],
                            order_by="idx"
                        )
                        
                        if not taxes or len(taxes) == 0:
                            errors.append(
                                _("La Plantilla de Impuesto '{0}' del item #{1} ({2}) no tiene líneas de impuesto configuradas.<br><br>"
                                  "Por favor, agregue al menos una línea de impuesto en la Plantilla de Impuesto.").format(
                                    tax_template_name,
                                    idx + 1,
                                    item.item_code or "Desconocido"
                                )
                            )
                        else:
                            # Validar que al menos una línea tenga sifen_tipo_iva configurado
                            has_sifen_tipo = False
                            has_positive_tax_rate = False  # Flag para verificar si hay al menos un impuesto con tasa > 0

                            for tax in taxes:
                                # Verificar si hay al menos un impuesto con tasa > 0
                                if tax.tax_rate and float(tax.tax_rate) > 0:
                                    has_positive_tax_rate = True
                                
                                if tax.sifen_tipo_iva:
                                    has_sifen_tipo = True
                                    # Validar que el valor sea válido (1-4)
                                    try:
                                        sifen_value = str(tax.sifen_tipo_iva).strip()
                                        if '|' in sifen_value:
                                            sifen_value = sifen_value.split('|')[0].strip()
                                        sifen_code = int(sifen_value)
                                        if sifen_code < 1 or sifen_code > 4:
                                            errors.append(
                                                _("La Plantilla de Impuesto '{0}' del item #{1} tiene un valor inválido para SIFEN Tipo IVA.<br><br>"
                                                  "Valor actual: {2}<br>"
                                                  "Valores permitidos: 1-4 (1=Gravado, 2=Exonerado, 3=Exento, 4=Parcial)").format(
                                                    tax_template_name,
                                                    idx + 1,
                                                    tax.sifen_tipo_iva
                                                )
                                            )
                                    except (ValueError, TypeError):
                                        errors.append(
                                            _("La Plantilla de Impuesto '{0}' del item #{1} tiene un valor no numérico para SIFEN Tipo IVA.<br><br>"
                                              "Valor actual: {2}<br>"
                                              "Valores permitidos: 1-4 (1=Gravado, 2=Exonerado, 3=Exento, 4=Parcial)").format(
                                                tax_template_name,
                                                idx + 1,
                                                tax.sifen_tipo_iva
                                            )
                                        )
                            
                            if not has_sifen_tipo:
                                errors.append(
                                    _("La Plantilla de Impuesto '{0}' del item #{1} ({2}) no tiene el campo 'SIFEN Tipo IVA' configurado en ninguna línea.<br><br>"
                                      "Por favor, configure el campo 'SIFEN Tipo IVA' en al menos una línea de impuesto.<br><br>"
                                      "Valores permitidos:<br>"
                                      "1 = Gravado IVA<br>"
                                      "2 = Exonerado (Art.83- Ley 125/91)<br>"
                                      "3 = Exento (no IVA)<br>"
                                      "4 = Gravado parcial").format(
                                        tax_template_name,
                                        idx + 1,
                                        item.item_code or "Desconocido"
                                    )
                                )
                            
                            # Validar que los clientes de Paraguay no tengan impuestos con 0%
                            # (excepto que sea tipo 2=Exonerado o 3=Exento)
                            # Verificar si el cliente es de Paraguay
                            is_paraguay_customer = (customer_country and customer_country == "Paraguay")

                            if is_paraguay_customer and not has_positive_tax_rate:
                                # Verificar si todos los impuestos son tipo Exento/Exonerado
                                all_exempt = True
                                for tax in taxes:
                                    if tax.sifen_tipo_iva:
                                        sifen_value = str(tax.sifen_tipo_iva).strip()
                                        if '|' in sifen_value:
                                            sifen_value = sifen_value.split('|')[0].strip()
                                        try:
                                            sifen_code = int(sifen_value)
                                            # 1=Gravado, 4=Parcial no son exentos
                                            if sifen_code in [1, 4]:
                                                all_exempt = False
                                                break
                                        except (ValueError, TypeError):
                                            pass
                                
                                # Si no son todos exentos y la tasa es 0%, mostrar error
                                if all_exempt == False:
                                    errors.append(
                                        _("La Plantilla de Impuesto '{0}' del item #{1} ({2}) tiene todos los impuestos con tasa 0%.<br><br>"
                                          "Para clientes de Paraguay, los items gravados con IVA deben tener una tasa de impuesto mayor a 0%.<br><br>"
                                          "Si el item es exento o exonerado, configure el campo 'SIFEN Tipo IVA' como:<br>"
                                          "2 = Exonerado (Art.83- Ley 125/91)<br>"
                                          "3 = Exento (no IVA)").format(
                                            tax_template_name,
                                            idx + 1,
                                            item.item_code or "Desconocido"
                                        )
                                    )
                    except Exception as e:
                        errors.append(
                            _("Error al validar la Plantilla de Impuesto '{0}' del item #{1}: {2}").format(
                                tax_template_name,
                                idx + 1,
                                str(e)
                            )
                        )

    # ============================================
    # Validar tabla Sales Taxes and Charges (Impuestos a nivel de factura)
    # ============================================
    # Esta tabla es donde ERPNext agrega impuestos por defecto
    if hasattr(doc, 'taxes') and doc.taxes:
        # Validar impuestos con 0% en clientes de Paraguay
        is_paraguay_customer = (customer_country and customer_country == "Paraguay")

        if is_paraguay_customer:
            has_zero_rate_tax = False
            zero_rate_taxes = []

            for tax in doc.taxes:
                # Verificar si la tasa es 0% o si no tiene tasa configurada
                if not tax.rate or float(tax.rate or 0) == 0:
                    has_zero_rate_tax = True
                    zero_rate_taxes.append(f"Row #{tax.idx}: {tax.account_head}")

            if has_zero_rate_tax:
                # Error bloqueante para el usuario
                errors.append(
                    _("La factura tiene impuestos con tasa 0% en la tabla 'Sales Taxes and Charges' (Impuestos y Cargos).<br><br>"
                      "<strong>Impuestos con 0%:</strong> {0}<br><br>"
                      "Para clientes de Paraguay, los impuestos deben tener una tasa mayor a 0%.<br><br>"
                      "<strong>Posible causa:</strong> ERPNext agregó automáticamente una plantilla de impuestos con tasa 0%.<br><br>"
                      "<strong>Solución:</strong> Elimine la fila de impuesto con 0% en la tabla 'Impuestos y Cargos' o seleccione una plantilla de impuestos con tasa válida.").format(
                        ", ".join(zero_rate_taxes)
                    )
                )
    else:
        # Si no hay impuestos en la tabla y el cliente es de Paraguay, mostrar error
        is_paraguay_customer = (customer_country and customer_country == "Paraguay")
        
        if is_paraguay_customer and hasattr(doc, 'grand_total') and doc.grand_total and doc.grand_total > 0:
            errors.append(
                _("La factura no tiene impuestos configurados en la tabla 'Sales Taxes and Charges' (Impuestos y Cargos).<br><br>"
                  "Para clientes de Paraguay, es obligatorio configurar al menos un impuesto.<br><br>"
                  "<strong>Posible causa:</strong> No se seleccionó una Plantilla de Impuestos (Item Tax Template) en los items o en el Item master.<br><br>"
                  "<strong>Solución:</strong><br>"
                  "1. Verifique que cada item tenga una Plantilla de Impuestos configurada<br>"
                  "2. Verifique que la Plantilla de Impuestos tenga al menos una línea con tasa > 0%<br>"
                  "3. Configure manualmente un impuesto en la tabla 'Impuestos y Cargos'")
            )

    # ============================================
    # Validar Número de Control (si ya existe)
    # ============================================
    if doc.custom_numero_control:
        # Validar que el número de control tenga 9 dígitos
        if len(str(doc.custom_numero_control)) != 9:
            errors.append(
                _("El Número de Control debe tener exactamente 9 dígitos.<br><br>"
                  "Valor actual: {0} (longitud: {1})").format(
                    doc.custom_numero_control,
                    len(str(doc.custom_numero_control))
                )
            )

        # Validar que el número de control sea numérico
        if not str(doc.custom_numero_control).isdigit():
            errors.append(
                _("El Número de Control debe contener solo dígitos.<br><br>"
                  "Valor actual: {0}").format(doc.custom_numero_control)
            )

    # ============================================
    # Validar Pagos (POS y Advances)
    # ============================================
    # Validar que la factura tenga método de pago configurado
    try:
        # Verificar si es factura POS (tiene pos_profile o payments)
        is_pos_invoice = False
        if hasattr(doc, 'is_pos') and doc.is_pos:
            is_pos_invoice = True
        elif hasattr(doc, 'pos_profile') and doc.pos_profile:
            is_pos_invoice = True

        if is_pos_invoice:
            # Para facturas POS, validar que tenga POS Payments configurados
            has_pos_payments = False
            has_payment_terms = False

            # Verificar Payments (métodos de pago en sección Pagos)
            if hasattr(doc, 'payments') and doc.payments:
                for payment in doc.payments:
                    if payment.amount and payment.amount > 0:
                        has_pos_payments = True
                        break

            # Verificar Payment Terms (términos de pago)
            if hasattr(doc, 'payment_schedule') and doc.payment_schedule:
                for term in doc.payment_schedule:
                    if term.due_date and term.payment_amount and term.payment_amount > 0:
                        has_payment_terms = True
                        break

            # Verificar Payment Terms Template (plantilla)
            if hasattr(doc, 'payment_terms_template') and doc.payment_terms_template:
                has_payment_terms = True

            # Debe tener al menos uno: Payments O Payment Terms
            if not has_pos_payments and not has_payment_terms:
                errors.append(
                    _("La factura POS no tiene métodos de pago configurados.<br><br>"
                      "Por favor, configure al menos una de las siguientes opciones:<br><br>"
                      "1. <strong>Pagos:</strong> Agregue al menos un método de pago en la sección 'Pagos' con monto mayor a cero<br>"
                      "2. <strong>Términos de Pago:</strong> Seleccione una plantilla en 'Payment Terms Template' o agregue términos en 'Payment Schedule'<br><br>"
                      "Actual:<br>"
                      f"- Payments (Pagos): {'✅' if has_pos_payments else '❌'}<br>"
                      f"- Payment Terms (Términos): {'✅' if has_payment_terms else '❌'}")
                )
        else:
            # Para facturas normales, validar que tenga Payment Terms o Advances
            has_payment_terms = False
            has_advances = False
            has_payment_terms_template = False

            # Verificar Payment Terms Template (plantilla)
            if hasattr(doc, 'payment_terms_template') and doc.payment_terms_template:
                has_payment_terms_template = True

            # Verificar Payment Schedule (términos generados desde plantilla o manuales)
            if hasattr(doc, 'payment_schedule') and doc.payment_schedule:
                for term in doc.payment_schedule:
                    if term.due_date and term.payment_amount and term.payment_amount > 0:
                        has_payment_terms = True
                        break

            # Verificar Advances (adelantos)
            if hasattr(doc, 'advances') and doc.advances:
                for advance in doc.advances:
                    if advance.allocated_amount and advance.allocated_amount > 0:
                        has_advances = True
                        break

            # Si no tiene ninguno, mostrar error bloqueante
            if not has_payment_terms and not has_advances and not has_payment_terms_template:
                # Solo validar si la factura tiene monto total > 0
                if hasattr(doc, 'grand_total') and doc.grand_total and doc.grand_total > 0:
                    errors.append(
                        _("La factura no tiene Términos de Pago ni Adelantos configurados.<br><br>"
                          "Por favor, configure al menos una de las siguientes opciones:<br><br>"
                          "1. <strong>Payment Terms Template:</strong> Seleccione una plantilla en el campo 'Payment Terms'<br>"
                          "2. <strong>Payment Schedule:</strong> Agregue términos manualmente en la tabla inferior<br>"
                          "3. <strong>Advances:</strong> Configure adelantos en la sección 'Advances' (si hay pagos anticipados)<br><br>"
                          "Este campo es necesario para determinar la condición de pago (Contado/Crédito).")
                    )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
    
    # Continuar con la validación de Payment Schedule (fuera del try/except)
    # Validar que los términos de pago tengan plazo configurado
    # Según SIFEN:
    # - Si condicion.credito.tipo = 1 (Plazo): plazo es obligatorio (2-15 caracteres)
    # - Si condicion.credito.tipo = 2 (Cuota): cuotas es obligatorio
    
    # Debug: verificar estado de payment_schedule
    has_payment_schedule = hasattr(doc, 'payment_schedule')
    payment_schedule_count = len(doc.payment_schedule) if has_payment_schedule else 0

    if has_payment_schedule and payment_schedule_count > 0:
        # Determinar si es operación a crédito (recalcular siempre)
        condicion_operacion = get_condicion_operacion(doc)
        is_credito = (condicion_operacion == 2)

        if is_credito:
            # Validar que haya al menos un término con plazo configurado
            has_valid_plazo = False

            for term in doc.payment_schedule:
                credit_days = term.credit_days if hasattr(term, 'credit_days') else None

                # Verificar que tenga credit_days configurado (para SIFEN tipo = 1)
                if credit_days and int(credit_days) > 0:
                    has_valid_plazo = True
                    break

            # Si no hay plazo válido, mostrar error
            if not has_valid_plazo:
                errors.append(
                    _("La factura es una operación a <strong>Crédito</strong> pero no tiene plazo configurado.<br><br>"
                      "<strong>Detalle de los términos:</strong><br>") +
                    "<br>".join([
                        f"- Item #{idx+1}: Credit Days = {t.credit_days if hasattr(t, 'credit_days') else 'N/A'}, Due Date = {t.due_date}"
                        for idx, t in enumerate(doc.payment_schedule)
                    ]) +
                    _("<br><br><strong>Posible causa:</strong> Se calculó automáticamente la fecha de vencimiento (due_date) pero no configuró el campo 'Credit Days' (Plazo de pago).<br><br>"
                      "<strong>Solución:</strong><br>"
                      "1. Configure una Plantilla de Términos de Pago con 'Days' > 0<br>"
                      "2. O complete manualmente el campo 'Credit Days' en la tabla Payment Schedule<br>"
                      "3. El valor debe ser > 0 (ej: 30, 60, 90 días)").format()
                )
            else:
                pass  # OK, tiene plazo configurado
    else:
        # Si no hay payment_schedule pero es crédito, mostrar error
        condicion_operacion = get_condicion_operacion(doc)
        if condicion_operacion == 2:
            errors.append(
                _("La factura es una operación a <strong>Crédito</strong> pero no tiene Términos de Pago configurados.<br><br>"
                  "Según el <strong>Manual Técnico SIFEN</strong>, las operaciones a crédito requieren al menos un término de pago con plazo configurado.<br><br>"
                  "<strong>Posible causa:</strong> Al desmarcar 'Incluir Pago (POS)', ERPNext eliminó los términos de pago.<br><br>"
                  "<strong>Solución:</strong><br>"
                  "1. Configure una Plantilla de Términos de Pago en el campo 'Payment Terms Template'<br>"
                  "2. O agregue manualmente términos en la tabla 'Payment Schedule'")
            )

    # ============================================
    # Lanzar todos los errores de una vez
    # ============================================
    if errors:
        frappe.throw(
            "<br><br>".join(errors),
            title=_("Campos Requeridos para E-Invoice (SIFEN)")
        )


def get_actividades_economicas(company):
    """
    Get economic activities for a company.

    Args:
        company: Company name or document

    Returns:
        List of dictionaries with 'codigo' and 'descripcion'
    """
    actividades = []

    try:
        company_doc = frappe.get_doc("Company", company) if isinstance(company, str) else company

        if hasattr(company_doc, 'actividades_economicas') and company_doc.actividades_economicas:
            for actividad in company_doc.actividades_economicas:
                actividades.append({
                    "codigo": actividad.codigo_actividad,
                    "descripcion": actividad.descripcion_actividad
                })
    except Exception:
        # Return empty list if lookup fails
        pass

    return actividades


def get_timbrado_info(company):
    """
    Get timbrado information from company.
    
    Args:
        company: Company name or document
        
    Returns:
        Dictionary with 'numero_timbrado' and 'fecha_timbrado'
    """
    timbrado = {
        "numero_timbrado": "",
        "fecha_timbrado": ""
    }
    
    try:
        company_doc = frappe.get_doc("Company", company) if isinstance(company, str) else company

        if hasattr(company_doc, 'numero_timbrado'):
            timbrado["numero_timbrado"] = company_doc.numero_timbrado or ""

        if hasattr(company_doc, 'fecha_timbrado') and company_doc.fecha_timbrado:
            # Convert date object to string for JSON serialization
            timbrado["fecha_timbrado"] = str(company_doc.fecha_timbrado)

    except Exception:
        # Return empty values if lookup fails
        pass

    return timbrado


def get_tipo_contribuyente(company):
    """
    Get contributor type from company.
    
    Args:
        company: Company name or document
        
    Returns:
        Integer: 1 = Persona Física, 2 = Persona Jurídica
    """
    tipo = 1  # Default: Persona Física
    
    try:
        company_doc = frappe.get_doc("Company", company) if isinstance(company, str) else company
        
        if hasattr(company_doc, 'tipo_contribuyente') and company_doc.tipo_contribuyente:
            # Convert to int if it's a string
            try:
                tipo = int(company_doc.tipo_contribuyente)
            except (ValueError, TypeError):
                tipo = 1
            
    except Exception:
        # Return default if lookup fails
        pass
    
    return tipo


def get_tipo_regimen(company):
    """
    Get tax regimen type from company.
    
    Args:
        company: Company name or document
        
    Returns:
        Integer: 1-8 (Turismo, Importador, Exportador, Maquila, Ley 60/90, Pequeño Productor, Mediano Productor, Contable)
    """
    tipo = 8  # Default: Régimen Contable
    
    try:
        company_doc = frappe.get_doc("Company", company) if isinstance(company, str) else company
        
        if hasattr(company_doc, 'tipo_regimen') and company_doc.tipo_regimen:
            # Convert to int if it's a string
            try:
                tipo = int(company_doc.tipo_regimen)
            except (ValueError, TypeError):
                tipo = 8
            
    except Exception:
        # Return default if lookup fails
        pass
    
    return tipo


def get_company_address(company_name):
    """
    Get address for a company.
    Priority:
    1. Preferred billing address (is_primary_address=1)
    2. First billing address found
    3. First office address found
    
    Returns dictionary with address fields and location codes.
    """
    address_data = {
        "address_line1": "",
        "address_line2": "",
        "city": "",
        "state": "",
        "country": "",
        "phone": "",
        "departamento": "",
        "departamentoDescripcion": "",
        "distrito": "",
        "distritoDescripcion": "",
        "ciudad": "",
        "ciudadDescripcion": ""
    }

    try:
        # Get all addresses linked to company
        all_addresses = frappe.get_all(
            "Dynamic Link",
            filters={"link_doctype": "Company", "link_name": company_name},
            fields=["parent as address_name"],
            as_list=False
        )

        address_names = [addr.address_name for addr in all_addresses]
        
        address = None

        # Priority 1: Try to get preferred billing address (is_primary_address=1)
        if address_names:
            try:
                address_doc = frappe.get_doc("Address", address_names[0])
                
                # Check if it matches our criteria
                if address_doc.address_type == "Billing" and address_doc.is_primary_address == 1:
                    address = {
                        "address_line1": address_doc.address_line1 or "",
                        "address_line2": address_doc.address_line2 or "",
                        "city": address_doc.city or "",
                        "state": address_doc.state or "",
                        "county": address_doc.county or "",
                        "sifen_numero_casa": address_doc.sifen_numero_casa or "",
                        "country": address_doc.country or "",
                        "phone": address_doc.phone or "",
                        "email_id": address_doc.email_id or ""
                    }
            except Exception:
                address = None

        # Priority 2: Try to get first billing address
        if not address and address_names:
            try:
                for addr_name in address_names:
                    address_doc = frappe.get_doc("Address", addr_name)
                    if address_doc.address_type == "Billing":
                        address = {
                            "address_line1": address_doc.address_line1 or "",
                            "address_line2": address_doc.address_line2 or "",
                            "city": address_doc.city or "",
                            "state": address_doc.state or "",
                            "county": address_doc.county or "",
                            "sifen_numero_casa": address_doc.sifen_numero_casa or "",
                            "country": address_doc.country or "",
                            "phone": address_doc.phone or "",
                            "email_id": address_doc.email_id or ""
                        }
                        break
            except Exception:
                pass

        # Priority 3: Try to get first office address
        if not address and address_names:
            try:
                for addr_name in address_names:
                    address_doc = frappe.get_doc("Address", addr_name)
                    if address_doc.address_type == "Office":
                        address = {
                            "address_line1": address_doc.address_line1 or "",
                            "address_line2": address_doc.address_line2 or "",
                            "city": address_doc.city or "",
                            "state": address_doc.state or "",
                            "county": address_doc.county or "",
                            "sifen_numero_casa": address_doc.sifen_numero_casa or "",
                            "country": address_doc.country or "",
                            "phone": address_doc.phone or "",
                            "email_id": address_doc.email_id or ""
                        }
                        break
            except Exception:
                pass

        # Fallback: Get any address linked to company
        if not address and address_names:
            try:
                address_doc = frappe.get_doc("Address", address_names[0])
                address = {
                    "address_line1": address_doc.address_line1 or "",
                    "address_line2": address_doc.address_line2 or "",
                    "city": address_doc.city or "",
                    "state": address_doc.state or "",
                    "county": address_doc.county or "",
                    "sifen_numero_casa": address_doc.sifen_numero_casa or "",
                    "country": address_doc.country or "",
                    "phone": address_doc.phone or "",
                    "email_id": address_doc.email_id or ""
                }
            except Exception:
                pass

        if address:
            address_data.update(address)

            # Parse state (departamento): "12|CENTRAL" → departamento=12, departamentoDescripcion=CENTRAL
            if address.get("state"):
                state_parts = address["state"].split("|", 1)
                if len(state_parts) == 2:
                    address_data["departamento"] = int(state_parts[0])
                    address_data["departamentoDescripcion"] = state_parts[1]

            # Parse county (distrito): "158|LIMPIO" → distrito=158, distritoDescripcion=LIMPIO
            if address.get("county"):
                county_parts = address["county"].split("|", 1)
                if len(county_parts) == 2:
                    address_data["distrito"] = int(county_parts[0])
                    address_data["distritoDescripcion"] = county_parts[1]

            # Parse city: "5940|LIMPIO (MUNICIPIO)" → ciudad=5940, ciudadDescripcion=LIMPIO (MUNICIPIO)
            if address.get("city"):
                city_parts = address["city"].split("|", 1)
                if len(city_parts) == 2:
                    address_data["ciudad"] = int(city_parts[0])
                    address_data["ciudadDescripcion"] = city_parts[1]
    except Exception as e:
        pass

    return address_data


def get_customer_address(sales_invoice):
    """
    Get customer address from sales invoice.

    Returns dictionary with address fields and location codes.
    """
    address_data = {
        "address_line1": "",
        "address_line2": "",
        "city": "",
        "state": "",
        "country": "Paraguay",
        "phone": "",
        "email_id": "",
        "departamento": None,
        "departamentoDescripcion": "",
        "distrito": None,
        "distritoDescripcion": "",
        "ciudad": None,
        "ciudadDescripcion": ""
    }

    # Try to get address from invoice
    if hasattr(sales_invoice, 'customer_address') and sales_invoice.customer_address:
        try:
            address_doc = frappe.get_doc("Address", sales_invoice.customer_address)
            address_data["address_line1"] = address_doc.address_line1 or ""
            address_data["address_line2"] = address_doc.address_line2 or ""
            address_data["city"] = address_doc.city or ""
            address_data["state"] = address_doc.state or ""
            address_data["country"] = address_doc.country or "Paraguay"
            address_data["phone"] = address_doc.phone or ""
            address_data["email_id"] = address_doc.email_id or ""
            address_data["sifen_numero_casa"] = address_doc.sifen_numero_casa or ""

            # Parse state (departamento): "12|CENTRAL" → departamento=12, departamentoDescripcion=CENTRAL
            if address_doc.state:
                state_parts = address_doc.state.split("|", 1)
                if len(state_parts) == 2:
                    address_data["departamento"] = int(state_parts[0])
                    address_data["departamentoDescripcion"] = state_parts[1]

            # Parse county (distrito): "158|LIMPIO" → distrito=158, distritoDescripcion=LIMPIO
            if address_doc.county:
                county_parts = address_doc.county.split("|", 1)
                if len(county_parts) == 2:
                    address_data["distrito"] = int(county_parts[0])
                    address_data["distritoDescripcion"] = county_parts[1]

            # Parse city: "5940|LIMPIO (MUNICIPIO)" → ciudad=5940, ciudadDescripcion=LIMPIO (MUNICIPIO)
            if address_doc.city:
                city_parts = address_doc.city.split("|", 1)
                if len(city_parts) == 2:
                    address_data["ciudad"] = int(city_parts[0])
                    address_data["ciudadDescripcion"] = city_parts[1]
        except Exception:
            pass
    else:
        # Get default billing address
        try:
            # Get all addresses linked to customer
            all_addresses = frappe.get_all(
                "Dynamic Link",
                filters={"link_doctype": "Customer", "link_name": sales_invoice.customer},
                fields=["parent as address_name"],
                as_list=False
            )
            
            address_names = [addr.address_name for addr in all_addresses]
            
            if address_names:
                # Try to get primary billing address first
                for addr_name in address_names:
                    address_doc = frappe.get_doc("Address", addr_name)
                    if address_doc.address_type == "Billing" and address_doc.is_primary_address == 1:
                        address_data["address_line1"] = address_doc.address_line1 or ""
                        address_data["address_line2"] = address_doc.address_line2 or ""
                        address_data["city"] = address_doc.city or ""
                        address_data["state"] = address_doc.state or ""
                        address_data["country"] = address_doc.country or "Paraguay"
                        address_data["phone"] = address_doc.phone or ""
                        address_data["email_id"] = address_doc.email_id or ""
                        address_data["sifen_numero_casa"] = address_doc.sifen_numero_casa or ""

                        # Parse location codes
                        if address_doc.state:
                            state_parts = address_doc.state.split("|", 1)
                            if len(state_parts) == 2:
                                address_data["departamento"] = int(state_parts[0])
                                address_data["departamentoDescripcion"] = state_parts[1]

                        if address_doc.county:
                            county_parts = address_doc.county.split("|", 1)
                            if len(county_parts) == 2:
                                address_data["distrito"] = int(county_parts[0])
                                address_data["distritoDescripcion"] = county_parts[1]

                        if address_doc.city:
                            city_parts = address_doc.city.split("|", 1)
                            if len(city_parts) == 2:
                                address_data["ciudad"] = int(city_parts[0])
                                address_data["ciudadDescripcion"] = city_parts[1]
                        break
        except Exception:
            pass

    return address_data


def get_usuario_from_invoice(sales_invoice):
    """
    Get user information from invoice owner or SIFEN responsible person from Company.
    Priority: SIFEN Responsible Person > Invoice Owner
    
    Returns dictionary with user data for data.usuario field.
    """
    import frappe
    
    usuario = {
        "documentoTipo": 1,
        "documentoNumero": "",
        "nombre": "Vendedor",
        "cargo": "Vendedor"
    }

    # First, try to get SIFEN responsible person from Company
    try:
        company = frappe.get_doc("Company", sales_invoice.company)
        
        # Debug: Log field values
        tipo_doc = getattr(company, 'sifen_responsable_tipo_documento', None)
        num_doc = getattr(company, 'sifen_respons_numero_documento', None)
        nombre = getattr(company, 'sifen_responsable_nombre', None)
        cargo = getattr(company, 'sifen_responsable_cargo', None)
        
        frappe.log_error(
            f"RJara | tipo:{tipo_doc} num:{num_doc} nombre:{nombre} cargo:{cargo}",
            "E-Invoice: SIFEN Responsible"
        )

        if tipo_doc:
            # Extract numeric value if stored as "1|C.I." format
            tipo_doc_str = str(tipo_doc)
            if "|" in tipo_doc_str:
                tipo_doc_str = tipo_doc_str.split("|")[0]
            usuario["documentoTipo"] = int(tipo_doc_str)

        if num_doc:
            usuario["documentoNumero"] = num_doc

        if nombre:
            usuario["nombre"] = nombre

        if cargo:
            usuario["cargo"] = cargo

        # Debug: Log final usuario
        frappe.log_error(
            f"usuario: {usuario}",
            "E-Invoice: Usuario Final"
        )
            
        # Return early if we found SIFEN responsible person data
        if usuario["documentoNumero"] or usuario["nombre"] != "Vendedor":
            return usuario
            
    except Exception as e:
        frappe.log_error(
            f"Error: {str(e)[:50]}",
            "E-Invoice: Error responsable"
        )
        pass

    # Fallback: Get user who created the invoice
    try:
        user_id = sales_invoice.owner or "Administrator"
        user = frappe.db.get_value(
            "User",
            user_id,
            ["full_name", "first_name"],
            as_dict=True
        )

        if user:
            usuario["nombre"] = user.full_name or user.first_name or "Vendedor"
    except Exception:
        pass

    return usuario


def get_tipo_transaccion(sales_invoice):
    """
    Determinar tipo de transacción según los items de la factura.

    Tipos posibles según Manual Técnico SIFEN v150 (D011):
    1 = Venta de mercadería
    2 = Prestación de servicios
    3 = Mixto (Venta de mercadería y servicios)
    4 = Venta de activo fijo
    5 = Venta de divisas
    6 = Compra de divisas
    7 = Promoción o entrega de muestras
    8 = Donación
    9 = Anticipo
    10 = Compra de productos
    11 = Compra de servicios
    12 = Venta de crédito fiscal
    13 = Muestras médicas

    Args:
        sales_invoice: Sales Invoice document

    Returns:
        int: Tipo de transacción (1, 2 o 3 principalmente)
    """
    has_products = False
    has_services = False
    has_fixed_asset = False

    for item in sales_invoice.items:
        # Get item type from Item doctype
        # ERPNext uses is_stock_item and is_fixed_asset flags
        item_data = frappe.db.get_value(
            "Item",
            item.item_code,
            ["is_stock_item", "is_fixed_asset"],
            as_dict=True
        )
        
        if item_data:
            if item_data.is_fixed_asset:
                has_fixed_asset = True
            elif item_data.is_stock_item:
                has_products = True
            else:
                has_services = True

    # Prioridad: Activo Fijo > Mixto > Servicios > Mercadería
    if has_fixed_asset:
        return 4  # Venta de activo fijo
    elif has_products and has_services:
        return 3  # Mixto
    elif has_services:
        return 2  # Prestación de servicios
    else:
        return 1  # Venta de mercadería (default)


def get_sifen_tipo_iva_item(item_code, item_tax_template=None, sales_invoice=None):
    """
    Get SIFEN IVA afectation code and tax rate from Item Tax Template Detail (child table).
    
    This function returns the ivaTipo code (1-4) for items, which represents
    how the item is affected by IVA (VAT).

    SIFEN D013 - codigosAfectaciones (ivaTipo):
    1 = Gravado IVA (item con IVA)
    2 = Exonerado (Art.83- Ley 125/91)
    3 = Exento (no IVA)
    4 = Gravado parcial (Grav- Exento)

    Args:
        item_code: Item code string
        item_tax_template: Item Tax Template name (optional, will fetch from Item if not provided)
        sales_invoice: Sales Invoice object (optional, used as fallback for tax type)

    Returns:
        tuple: (afectacion_code, tax_rate)
            - afectacion_code: int (default: 1 - Gravado IVA)
            - tax_rate: float (default: 10.0)
    """
    if not item_code:
        return 1, 10.0

    # Get item's tax template from parameter or fetch from Item
    if not item_tax_template:
        try:
            item_tax_template = frappe.db.get_value(
                "Item",
                item_code,
                "item_tax_template"
            )
        except Exception:
            # Field may not exist in some ERPNext versions
            item_tax_template = None

    # If item has tax template, use it
    if item_tax_template:
        # Get taxes from Item Tax Template Detail (child table)
        taxes = frappe.db.get_all(
            "Item Tax Template Detail",
            filters={"parent": item_tax_template},
            fields=["sifen_tipo_iva", "tax_rate", "tax_type"],
            order_by="idx"
        )

        if taxes:
            for tax in taxes:
                # First priority: use sifen_tipo_iva field if set
                if tax.sifen_tipo_iva:
                    try:
                        # Extract numeric code before pipe if present (e.g., "2|Exonerado" → 2)
                        sifen_value = str(tax.sifen_tipo_iva).strip()
                        if '|' in sifen_value:
                            sifen_value = sifen_value.split('|')[0].strip()

                        sifen_type = int(sifen_value)
                        tax_rate = float(tax.tax_rate) if tax.tax_rate else 10.0
                        return sifen_type, tax_rate
                    except (ValueError, TypeError):
                        pass

                # Fallback: determine SIFEN type from tax_type name
                if tax.tax_type:
                    tax_type_lower = tax.tax_type.lower()
                    tax_rate = float(tax.tax_rate) if tax.tax_rate else 10.0

                    # Map common tax type names to SIFEN afectation codes
                    if 'iva' in tax_type_lower:
                        return 1, tax_rate  # Gravado IVA
                    elif 'isc' in tax_type_lower or 'selectivo' in tax_type_lower:
                        return 3, tax_rate  # Exento (ISC no es IVA)
                    elif 'renta' in tax_type_lower or 'ir' in tax_type_lower:
                        return 3, tax_rate  # Exento (Renta no es IVA)
                    elif 'exento' in tax_type_lower or 'exon' in tax_type_lower:
                        return 3, tax_rate  # Exento
                    elif 'ninguno' in tax_type_lower or 'sin' in tax_type_lower:
                        return 3, tax_rate  # Exento

    # Fallback: If no item tax template, use default (Gravado IVA)
    # Note: We don't use get_sifen_tipo_impuesto() here because that returns
    # tipoImpuesto (1-5, from customer) not ivaTipo (1-4, for items)
    return 1, 10.0  # Default: Gravado IVA


def get_sifen_tipo_impuesto(sales_invoice):
    """
    Get SIFEN tax type from customer field (sifen_tipo_impuesto).

    SIFEN D013 - tiposImpuestos (nivel factura):
    1 = IVA (cliente local contribuyente)
    2 = ISC (productos con impuesto selectivo)
    3 = Renta (cliente extranjero B2F con RUC)
    4 = Ninguno (cliente extranjero sin RUC, consumidor final)
    5 = IVA - Renta (mixto)

    This field is now manually selected in Customer record.

    Args:
        sales_invoice: Sales Invoice document

    Returns:
        tuple: (tipo_impuesto, tax_rate)
            - tipo_impuesto: int (1-5) from tiposImpuestos
            - tax_rate: float (default: 10.0 for IVA/ISC, 0.0 for Ninguno)
    """
    # Get customer data with sifen_tipo_impuesto field
    customer = None
    
    if hasattr(sales_invoice, 'customer') and sales_invoice.customer:
        customer = frappe.db.get_value(
            "Customer",
            sales_invoice.customer,
            ["sifen_tipo_impuesto", "tax_id"],
            as_dict=True
        )

    # Get tipoImpuesto from customer field
    if customer and customer.sifen_tipo_impuesto:
        # Extract numeric value from stored format (e.g., "1|IVA" → 1)
        tipo_impuesto_str = str(customer.sifen_tipo_impuesto).strip()
        if '|' in tipo_impuesto_str:
            tipo_impuesto_str = tipo_impuesto_str.split('|')[0].strip()
        
        try:
            tipo_impuesto = int(tipo_impuesto_str)
            
            # Validate range (1-5)
            if tipo_impuesto < 1 or tipo_impuesto > 5:
                frappe.throw(
                    _("Invalid SIFEN Tipo Impuesto value for customer {0}: {1}.<br><br>"
                      "Valid values are 1-5.").format(
                        sales_invoice.customer,
                        tipo_impuesto
                    ),
                    title=_("Invalid SIFEN Tipo Impuesto")
                )
            
            # Return tax rate based on tipoImpuesto
            if tipo_impuesto == 4:  # Ninguno
                return tipo_impuesto, 0.0
            else:
                return tipo_impuesto, 10.0  # Default rate for IVA/ISC/Renta
                
        except (ValueError, TypeError):
            frappe.throw(
                _("Invalid SIFEN Tipo Impuesto format for customer {0}: {1}.<br><br>"
                  "Please select a valid option (1-5).").format(
                    sales_invoice.customer,
                    customer.sifen_tipo_impuesto
                ),
                title=_("Invalid SIFEN Tipo Impuesto Format")
            )
    
    # Fallback: Default to IVA (1) if field is not set
    # This should not happen as the field is validated in validar_campos_sifen()
    return 1, 10.0


def get_sifen_unidad_medida(stock_uom):
    """
    Map ERPNext UOM to SIFEN unidadMedida codes.
    
    Args:
        stock_uom: ERPNext stock UOM (e.g., "Nos", "Kg", "Litros")
    
    Returns:
        int: SIFEN unidadMedida code (default: 77 - Unidad)
    """
    if not stock_uom:
        return 77  # Default: Unidad
    
    uom_lower = stock_uom.lower().strip()
    
    # Peso/Masa
    if 'kg' in uom_lower or 'kilo' in uom_lower or 'kilogramo' in uom_lower:
        return 83  # kg - Kilogramos
    elif 'gr' in uom_lower or 'gramo' in uom_lower:
        return 86  # g - Gramos
    elif 'mg' in uom_lower or 'miligramo' in uom_lower:
        return 90  # MG - Miligramos
    elif 'tn' in uom_lower or 'tonelada' in uom_lower:
        return 99  # TN - Tonelada
    
    # Volumen/Líquidos
    elif 'lt' in uom_lower or 'litro' in uom_lower:
        return 89  # LT - Litros
    elif 'ml' in uom_lower or 'mililitro' in uom_lower:
        return 88  # ML - Mililitros
    elif 'm3' in uom_lower or 'metro cubico' in uom_lower:
        return 110  # M3 - Metros cúbicos
    
    # Longitud
    elif 'm' == uom_lower or uom_lower.startswith('metro') or 'mt' in uom_lower:
        return 108  # MT - Metros
    elif 'km' in uom_lower or 'kilometro' in uom_lower:
        return 625  # Km - Kilómetros
    elif 'cm' in uom_lower and 'cuadr' not in uom_lower:
        return 91  # CM - Centímetros
    elif 'mm' in uom_lower and 'cuadr' not in uom_lower:
        return 95  # MM - Milímetros
    elif 'pulg' in uom_lower:
        return 94  # PUL - Pulgadas
    elif 'yard' in uom_lower:
        return 103  # Ya - Yardas
    
    # Superficie
    elif 'm2' in uom_lower or 'metro cuadrado' in uom_lower:
        return 109  # M2 - Metros cuadrados
    elif 'cm2' in uom_lower or 'cm cuadrado' in uom_lower:
        return 92  # CM2 - Centímetros cuadrados
    elif 'mm2' in uom_lower or 'mm cuadrado' in uom_lower:
        return 96  # MM2 - Milímetros cuadrados
    elif 'ha' in uom_lower or 'hectarea' in uom_lower:
        return 869  # ha - Hectáreas
    
    # Tiempo
    elif 'hora' in uom_lower or 'hr' in uom_lower:
        return 100  # Hs - Hora
    elif 'minuto' in uom_lower or 'min' in uom_lower:
        return 101  # Mi - Minuto
    elif 'dia' in uom_lower or 'día' in uom_lower or 'day' in uom_lower:
        return 102  # Di - Día
    elif 'mes' in uom_lower:
        return 98  # ME - Mes
    elif 'año' in uom_lower or 'anio' in uom_lower or 'year' in uom_lower:
        return 97  # AA - Año
    elif 'segundo' in uom_lower or 'seg' in uom_lower:
        return 666  # Se - Segundo
    
    # Otros
    elif 'unidad' in uom_lower or 'nos' in uom_lower or 'pieza' in uom_lower:
        return 77  # UNI - Unidad
    elif 'global' in uom_lower or 'lote' in uom_lower:
        return 885  # GL - Unidad Medida Global
    elif 'ral' in uom_lower:  # Ración
        return 569  # ración - Ración
    
    # Default: Unidad
    return 77


def prepare_items_data(sales_invoice):
    """
    Prepare items data for the invoice.

    Returns list of item dictionaries.
    """
    items = []

    # Get currency from invoice (needed for discount rounding and exchange rate)
    moneda = sales_invoice.currency or "PYG"

    for item in sales_invoice.items:
        # Get item details from Item doctype
        # Note: item_tax_template is in Sales Invoice Item, not in Item
        item_details = frappe.db.get_value(
            "Item",
            item.item_code,
            ["item_code", "stock_uom"],
            as_dict=True
        )

        # Get item_tax_template from Sales Invoice Item (child table)
        # This overrides the Item master's tax template if set in the invoice
        item_tax_template = None
        if hasattr(item, 'item_tax_template') and item.item_tax_template:
            item_tax_template = item.item_tax_template
        elif item_details and hasattr(item_details, 'item_tax_template'):
            # Fallback to Item master's tax template
            item_tax_template = item_details.item_tax_template

        # Get SIFEN IVA afectation code and tax rate from Item Tax Template Detail (child table)
        # Pass sales_invoice as fallback if item has no tax template
        iva_tipo, iva_tasa = get_sifen_tipo_iva_item(item.item_code, item_tax_template, sales_invoice)

        # Determine ivaProporcion based on ivaTipo
        # SIFEN D013 - ivaProporcion: Percentage of VAT application (0-100)
        # - 100 = Full VAT application (gravado)
        # - 0 = No VAT application (exento)
        if iva_tipo == 3:  # Exento/Ninguno
            iva_proporcion = 0
        elif iva_tipo == 4:  # Ninguno (no gravado)
            iva_proporcion = 0
        else:  # 1=IVA, 2=ISC, 5=IVA-Renta
            iva_proporcion = 100

        # Use actual tax rate from Item Tax Template (not hardcoded)
        # Default: 10% for IVA, 0% for others
        if iva_tipo in [1, 5]:  # IVA or IVA-Renta
            iva = iva_tasa  # ✅ Dynamic: Use actual rate from template
        else:
            iva = 0  # ISC, Exento, Ninguno

        # Calculate unit price without tax
        precio_unitario = item.rate

        # Map unit of measure to SIFEN codes using comprehensive mapping
        unidad_medida = get_sifen_unidad_medida(item_details.stock_uom if item_details else None)

        # Get exchange rate for item
        # If currency is PYG, cambio = 0
        # If foreign currency, use invoice conversion_rate
        # Note: SIFEN requires cambio = 0 for PYG, real value for foreign currencies
        cambio_item = 0  # Default for PYG
        
        if moneda != "PYG" and hasattr(sales_invoice, 'conversion_rate'):
            # For foreign currency, use the invoice conversion rate
            # Only set if > 1 (handles edge case where conversion_rate = 1.0)
            if sales_invoice.conversion_rate and sales_invoice.conversion_rate > 1:
                cambio_item = sales_invoice.conversion_rate

        # Get discount amount for item
        # ERPNext has two discount fields:
        # - discount_amount: Fixed discount on this item
        # - distributed_discount_amount: Portion of document-level discount allocated to this item
        descuento_item = 0
        
        if hasattr(item, 'discount_amount') and item.discount_amount:
            descuento_item = float(item.discount_amount)
        elif hasattr(item, 'distributed_discount_amount') and item.distributed_discount_amount:
            descuento_item = float(item.distributed_discount_amount)
        
        # Round discount according to SIFEN rules (same as descuentoGlobal)
        if descuento_item > 0:
            if moneda == "PYG":
                # PYG: no decimals (integer)
                descuento_item = round(descuento_item)
            else:
                # Foreign currency: max 8 decimals
                descuento_item = round(descuento_item, 8)

        # Get advance payment amount for item
        # NOTE: ERPNext does not track advances at item level natively
        # Advances are only available at invoice level (total_advance, advances[])
        # For SIFEN, we use anticipoGlobal for global advances (condicionAnticipo = 1)
        # Item-level advances (condicionAnticipo = 2) are not supported by ERPNext
        anticipo_item = 0  # Always 0 - ERPNext only supports global advances

        # Get country of origin for item
        # ERPNext has country_of_origin field in Item Doctype (Link to Country)
        # For SIFEN, we need ISO 3166-1 alpha-3 country code (3 letters)
        # Default: PRY (Paraguay) for domestic items
        pais_item = "PRY"
        pais_descripcion = "Paraguay"
        
        if item_details and item_details.country_of_origin:
            # Get country code and description from ERPNext Country Doctype
            country_data = frappe.db.get_value(
                "Country",
                item_details.country_of_origin,
                ["code", "country_name"],
                as_dict=True
            )
            
            if country_data and country_data.code:
                # ERPNext uses ISO 3166-1 alpha-2 (2 letters), SIFEN needs alpha-3 (3 letters)
                # Common conversions for Paraguay trading partners
                alpha2_to_alpha3 = {
                    "PY": ("PRY", "Paraguay"),
                    "AR": ("ARG", "Argentina"),
                    "BR": ("BRA", "Brasil"),
                    "US": ("USA", "Estados Unidos"),
                    "CN": ("CHN", "China"),
                    "CL": ("CHL", "Chile"),
                    "UY": ("URY", "Uruguay"),
                    "BO": ("BOL", "Bolivia"),
                    "DE": ("DEU", "Alemania"),
                    "ES": ("ESP", "España"),
                    "MX": ("MEX", "México"),
                    "CO": ("COL", "Colombia"),
                    "PE": ("PER", "Perú"),
                    "EC": ("ECU", "Ecuador"),
                    "JP": ("JPN", "Japón"),
                    "KR": ("KOR", "Corea del Sur"),
                    "IT": ("ITA", "Italia"),
                    "FR": ("FRA", "Francia"),
                    "GB": ("GBR", "Reino Unido"),
                    "CA": ("CAN", "Canadá"),
                    "AU": ("AUS", "Australia"),
                    "IN": ("IND", "India"),
                    "RU": ("RUS", "Rusia"),
                    "ZA": ("ZAF", "Sudáfrica"),
                    "EG": ("EGY", "Egipto"),
                    "NG": ("NGA", "Nigeria"),
                    "KE": ("KEN", "Kenia"),
                    "GH": ("GHA", "Ghana"),
                    "MA": ("MAR", "Marruecos"),
                    "TN": ("TUN", "Túnez"),
                    "DZ": ("DZA", "Argelia"),
                    "LY": ("LBY", "Libia"),
                    "SD": ("SDN", "Sudán"),
                    "ET": ("ETH", "Etiopía"),
                    "TZ": ("TZA", "Tanzania"),
                    "UG": ("UGA", "Uganda"),
                    "ZW": ("ZWE", "Zimbabue"),
                    "ZM": ("ZMB", "Zambia"),
                    "MW": ("MWI", "Malawi"),
                    "MZ": ("MOZ", "Mozambique"),
                    "AO": ("AGO", "Angola"),
                    "CM": ("CMR", "Camerún"),
                    "CI": ("CIV", "Costa de Marfil"),
                    "SN": ("SEN", "Senegal"),
                    "ML": ("MLI", "Malí"),
                    "BF": ("BFA", "Burkina Faso"),
                    "NE": ("NER", "Níger"),
                    "TD": ("TCD", "Chad"),
                    "CF": ("CAF", "República Centroafricana"),
                    "CG": ("COG", "Congo"),
                    "CD": ("COD", "República Democrática del Congo"),
                    "GA": ("GAB", "Gabón"),
                    "GQ": ("GNQ", "Guinea Ecuatorial"),
                    "ST": ("STP", "Santo Tomé y Príncipe"),
                    "CV": ("CPV", "Cabo Verde"),
                    "GW": ("GNB", "Guinea-Bissau"),
                    "GN": ("GIN", "Guinea"),
                    "SL": ("SLE", "Sierra Leona"),
                    "LR": ("LBR", "Liberia"),
                }
                
                country_code = country_data.code.upper()
                if country_code in alpha2_to_alpha3:
                    pais_item = alpha2_to_alpha3[country_code][0]
                    pais_descripcion = alpha2_to_alpha3[country_code][1]
                else:
                    # Fallback: use country name if no conversion found
                    pais_descripcion = country_data.country_name or "Desconocido"
                    # Try to get alpha-3 code from country doctype if available
                    alpha3 = frappe.db.get_value("Country", item_details.country_of_origin, "code_alpha3")
                    if alpha3:
                        pais_item = alpha3
                    else:
                        # Last resort: use first 3 letters of country name
                        pais_item = pais_descripcion[:3].upper()

        items.append({
            "codigo": item.item_code,
            "descripcion": clean_html(item.description) or item.item_name or "Sin descripcion",
            "observacion": "",
            "unidadMedida": unidad_medida,
            "cantidad": item.qty,
            "precioUnitario": precio_unitario,
            "cambio": cambio_item,
            "descuento": descuento_item,
            "anticipo": anticipo_item,
            "pais": pais_item,
            "paisDescripcion": pais_descripcion,
            "ivaTipo": iva_tipo,  # ✅ Código de afectación (1-4) desde sifen_tipo_iva
            "ivaProporcion": iva_proporcion,
            "iva": iva
        })

    return items


def get_condicion_anticipo(sales_invoice):
    """
    Determine anticipo condition based on ERPNext advance payments.
    
    SIFEN D019 - iCondAnt:
    1 = Anticipo Global (un solo anticipo para todo el DE)
    2 = Anticipo por ítem (distribución de anticipos por ítem)
    
    Args:
        sales_invoice: Sales Invoice document
    
    Returns:
        int: 1 = Global, 2 = Por Ítem
    """
    # Check if there are advances allocated in the advances table
    if hasattr(sales_invoice, 'advances') and sales_invoice.advances:
        # Multiple advances = Por Ítem
        # Single advance = Global
        if len(sales_invoice.advances) > 1:
            return 2  # Por Ítem
        else:
            return 1  # Global
    
    # Check total_advance field
    if hasattr(sales_invoice, 'total_advance') and sales_invoice.total_advance > 0:
        return 1  # Global (single advance amount)
    
    # No advances - default to Global
    return 1


def validate_anticipo_before_submit(sales_invoice):
    """
    Validate that advance payments are properly allocated before submitting to SIFEN.
    
    SIFEN does not allow changing anticipoGlobal from 0 to positive after submission.
    This validation ensures all available advances are allocated before sending.
    
    Args:
        sales_invoice: Sales Invoice document
    
    Raises:
        frappe.ValidationError: If there are unallocated advances available
    """
    # Check if there are unallocated advances for this customer
    if not hasattr(sales_invoice, 'customer') or not sales_invoice.customer:
        return
    
    # Get available advances for this customer (Payment Entries with unallocated amount)
    unallocated_advances = frappe.db.sql("""
        SELECT 
            pe.name as payment_entry,
            pe.party,
            pe.unallocated_amount,
            pe.posting_date
        FROM `tabPayment Entry` pe
        WHERE pe.party_type = 'Customer'
        AND pe.party = %s
        AND pe.docstatus = 1
        AND pe.unallocated_amount > 0
        AND pe.payment_type = 'Receive'
        ORDER BY pe.posting_date ASC
    """, (sales_invoice.customer,), as_dict=True)
    
    if unallocated_advances:
        total_unallocated = sum(adv.unallocated_amount for adv in unallocated_advances)
        
        # Warning message (not blocking, just informative)
        warning_msg = f"""
            <b>⚠️ Hay anticipos sin asignar para este cliente</b><br><br>
            
            <b>Total sin asignar:</b> {frappe.format_value(total_unallocated, {'fieldtype': 'Currency'})}<br>
            <b>Cantidad de anticipos:</b> {len(unallocated_advances)}<br><br>
            
            <b>Anticipos disponibles:</b><br>
            <ul>
        """
        
        for adv in unallocated_advances[:5]:  # Show first 5
            warning_msg += f"<li>{adv.payment_entry}: {frappe.format_value(adv.unallocated_amount, {'fieldtype': 'Currency'})}</li>"
        
        if len(unallocated_advances) > 5:
            warning_msg += f"<li>... y {len(unallocated_advances) - 5} más</li>"
        
        warning_msg += """
            </ul><br>
            <b>Importante:</b> SIFEN no permite cambiar los anticipos después del envío.
            Si hay anticipos sin asignar, debe asignarlos ANTES de enviar la factura electrónicamente.<br><br>
            Para asignar anticipos:<br>
            1. Vaya a la sección <b>"Advance Payments"</b><br>
            2. Click en <b>"Get Advances Received"</b><br>
            3. Seleccione los anticipos y asígnelos<br>
            4. Guarde y vuelva a enviar a SIFEN
        """
        
        frappe.msgprint(warning_msg, title="Anticipos Sin Asignar", indicator='orange')


def get_credito_info(sales_invoice):
    """
    Get credit information from Sales Invoice payment terms.
    
    SIFEN credito types:
    1 = Con Plazo (single due date)
    2 = En Cuotas (multiple installments)
    
    Args:
        sales_invoice: Sales Invoice document
    
    Returns:
        dict: Credit information with 'tipo' and 'plazo' or 'cuotas'
        None: If no credit information available
    """
    # Check if invoice has payment schedule
    if hasattr(sales_invoice, 'payment_schedule') and sales_invoice.payment_schedule:
        # Multiple payment schedules = En Cuotas (tipo = 2)
        if len(sales_invoice.payment_schedule) > 1:
            return {
                "tipo": 2,  # En Cuotas
                "cuotas": len(sales_invoice.payment_schedule)
            }
        
        # Single payment schedule = Con Plazo (tipo = 1)
        if len(sales_invoice.payment_schedule) == 1:
            due_date = sales_invoice.payment_schedule[0].due_date
            if due_date and sales_invoice.posting_date:
                # Calculate days difference
                days_diff = (due_date - sales_invoice.posting_date).days
                return {
                    "tipo": 1,  # Con Plazo
                    "plazo": max(0, days_diff)  # Ensure non-negative
                }
    
    # Check payment terms template
    if hasattr(sales_invoice, 'payment_terms_template') and sales_invoice.payment_terms_template:
        # Try to get default credit days from template
        template = frappe.db.get_value(
            "Payment Terms Template",
            sales_invoice.payment_terms_template,
            ["template_name"],
            as_dict=True
        )
        
        if template:
            # Check if template has multiple terms (cuotas)
            terms = frappe.db.get_all(
                "Payment Term",
                filters={"parent": sales_invoice.payment_terms_template},
                fields=["*"],
                order_by="idx"
            )
            
            if len(terms) > 1:
                return {
                    "tipo": 2,  # En Cuotas
                    "cuotas": len(terms)
                }
            elif len(terms) == 1:
                # Single term with credit days
                credit_days = terms[0].credit_days or 30
                return {
                    "tipo": 1,  # Con Plazo
                    "plazo": credit_days
                }
    
    # Default: Con Plazo 30 days
    return {
        "tipo": 1,
        "plazo": 30
    }


def get_condicion_entregas(sales_invoice, moneda, condicion_tipo_cambio):
    """
    Build condicion.entregas array from ERPNext payments table.
    
    ERPNext Sales Invoice Payment child table contains:
    - mode_of_payment: Payment method (Cash, Bank, Card, etc.)
    - amount: Payment amount
    - account: Cash/Bank account
    
    SIFEN requires:
    - tipo: Payment type code (1-21, 99)
    - monto: Payment amount
    - moneda: Currency
    - cambio: Exchange rate condition
    
    Args:
        sales_invoice: Sales Invoice document
        moneda: Invoice currency
        condicion_tipo_cambio: Exchange rate condition (1=Global, 2=Por ítem)
    
    Returns:
        list: List of payment entregas
    """
    entregas = []
    
    # Check if invoice has payments child table
    if hasattr(sales_invoice, 'payments') and sales_invoice.payments:
        # Multiple payments - create entrega for each
        for payment in sales_invoice.payments:
            if hasattr(payment, 'mode_of_payment') and payment.mode_of_payment:
                # Get payment type from mode of payment
                tipo_pago = get_tipo_pago_sifen_from_mode(payment.mode_of_payment)
                
                # Get payment amount
                monto = str(payment.amount) if hasattr(payment, 'amount') else "0"
                
                entregas.append({
                    "tipo": tipo_pago,
                    "monto": monto,
                    "moneda": moneda,
                    "cambio": condicion_tipo_cambio if moneda != "PYG" else 1
                })
    
    # If no payments or payments table is empty, use single entrega with total
    if not entregas:
        # Get total paid amount
        total_pago = sales_invoice.grand_total or 0
        
        # Get payment type from invoice mode_of_payment
        tipo_pago = get_tipo_pago_sifen(sales_invoice)
        
        entregas.append({
            "tipo": tipo_pago,
            "monto": str(total_pago),
            "moneda": moneda,
            "cambio": condicion_tipo_cambio if moneda != "PYG" else 1
        })
    
    return entregas


def get_tipo_pago_sifen_from_mode(mode_of_payment):
    """
    Helper function to get SIFEN payment type from mode of payment string.
    
    Args:
        mode_of_payment: Payment mode string
    
    Returns:
        int: SIFEN payment type code
    """
    mode = mode_of_payment.lower()
    
    # Map ERPNext payment methods to SIFEN codes
    if 'efectivo' in mode or 'cash' in mode or 'contado' in mode:
        return 1  # Efectivo
    elif 'cheque' in mode or 'check' in mode:
        return 2  # Cheque
    elif 'tarjeta credito' in mode or 'credit card' in mode or 'tarjeta de crédito' in mode:
        return 3  # Tarjeta de crédito
    elif 'tarjeta debito' in mode or 'debit card' in mode or 'tarjeta de débito' in mode:
        return 4  # Tarjeta de débito
    elif 'transferencia' in mode or 'transfer' in mode or 'bank transfer' in mode:
        return 5  # Transferencia
    elif 'giro' in mode:
        return 6  # Giro
    elif 'billetera' in mode or 'wallet' in mode or 'móvil' in mode or 'movil' in mode:
        return 7  # Billetera electrónica
    elif 'tarjeta empresarial' in mode or 'corporate card' in mode:
        return 8  # Tarjeta empresarial
    elif 'vale' in mode or 'voucher' in mode:
        return 9  # Vale
    elif 'retención' in mode or 'retencion' in mode or 'withholding' in mode:
        return 10  # Retención
    elif 'anticipo' in mode or 'advance' in mode:
        return 11  # Pago por anticipo
    elif 'fiscal' in mode:
        return 12  # Valor fiscal
    elif 'comercial' in mode or 'commercial' in mode:
        return 13  # Valor comercial
    elif 'compensación' in mode or 'compensacion' in mode or 'compensation' in mode:
        return 14  # Compensación
    elif 'permuta' in mode or 'exchange' in mode:
        return 15  # Permuta
    elif 'pago bancario' in mode or 'bank payment' in mode:
        return 16  # Pago bancario
    elif 'pago móvil' in mode or 'pago movil' in mode or 'mobile payment' in mode:
        return 17  # Pago Móvil
    elif 'donación' in mode or 'donacion' in mode or 'donation' in mode:
        return 18  # Donación
    elif 'promoción' in mode or 'promocion' in mode or 'promotion' in mode:
        return 19  # Promoción
    elif 'consumo interno' in mode or 'consumo' in mode:
        return 20  # Consumo Interno
    elif 'pago electrónico' in mode or 'pago electronico' in mode or 'electronic payment' in mode:
        return 21  # Pago Electrónico
    else:
        return 99  # Otro


def get_tipo_pago_sifen(sales_invoice):
    """
    Determine SIFEN payment type (condicion.entregas[].tipo) from ERPNext mode of payment.
    
    SIFEN D020 - condicionesTiposPagos:
    1 = Efectivo
    2 = Cheque
    3 = Tarjeta de crédito
    4 = Tarjeta de débito
    5 = Transferencia
    6 = Giro
    7 = Billetera electrónica
    8 = Tarjeta empresarial
    9 = Vale
    10 = Retención
    11 = Pago por anticipo
    12 = Valor fiscal
    13 = Valor comercial
    14 = Compensación
    15 = Permuta
    16 = Pago bancario
    17 = Pago Móvil
    18 = Donación
    19 = Promoción
    20 = Consumo Interno
    21 = Pago Electrónico
    99 = Otro
    
    Args:
        sales_invoice: Sales Invoice document
    
    Returns:
        int: SIFEN payment type code (default: 1 - Efectivo)
    """
    # Check if invoice has mode of payment
    if hasattr(sales_invoice, 'mode_of_payment') and sales_invoice.mode_of_payment:
        mode = sales_invoice.mode_of_payment.lower()
        
        # Map ERPNext payment methods to SIFEN codes
        if 'efectivo' in mode or 'cash' in mode or 'contado' in mode:
            return 1  # Efectivo
        elif 'cheque' in mode or 'check' in mode:
            return 2  # Cheque
        elif 'tarjeta credito' in mode or 'credit card' in mode or 'tarjeta de crédito' in mode:
            return 3  # Tarjeta de crédito
        elif 'tarjeta debito' in mode or 'debit card' in mode or 'tarjeta de débito' in mode:
            return 4  # Tarjeta de débito
        elif 'transferencia' in mode or 'transfer' in mode or 'bank transfer' in mode:
            return 5  # Transferencia
        elif 'giro' in mode:
            return 6  # Giro
        elif 'billetera' in mode or 'wallet' in mode or 'móvil' in mode or 'movil' in mode:
            return 7  # Billetera electrónica
        elif 'tarjeta empresarial' in mode or 'corporate card' in mode:
            return 8  # Tarjeta empresarial
        elif 'vale' in mode or 'voucher' in mode:
            return 9  # Vale
        elif 'retención' in mode or 'retencion' in mode or 'withholding' in mode:
            return 10  # Retención
        elif 'anticipo' in mode or 'advance' in mode:
            return 11  # Pago por anticipo
        elif 'fiscal' in mode:
            return 12  # Valor fiscal
        elif 'comercial' in mode or 'commercial' in mode:
            return 13  # Valor comercial
        elif 'compensación' in mode or 'compensacion' in mode or 'compensation' in mode:
            return 14  # Compensación
        elif 'permuta' in mode or 'exchange' in mode:
            return 15  # Permuta
        elif 'pago bancario' in mode or 'bank payment' in mode:
            return 16  # Pago bancario
        elif 'pago móvil' in mode or 'pago movil' in mode or 'mobile payment' in mode:
            return 17  # Pago Móvil
        elif 'donación' in mode or 'donacion' in mode or 'donation' in mode:
            return 18  # Donación
        elif 'promoción' in mode or 'promocion' in mode or 'promotion' in mode:
            return 19  # Promoción
        elif 'consumo interno' in mode or 'consumo' in mode:
            return 20  # Consumo Interno
        elif 'pago electrónico' in mode or 'pago electronico' in mode or 'electronic payment' in mode:
            return 21  # Pago Electrónico
    
    # Check payments child table for multiple payment methods
    if hasattr(sales_invoice, 'payments') and sales_invoice.payments:
        # If there are multiple payments, use the first one's mode
        first_payment = sales_invoice.payments[0]
        if hasattr(first_payment, 'mode_of_payment') and first_payment.mode_of_payment:
            mode = first_payment.mode_of_payment.lower()
            # Apply same mapping as above
            if 'efectivo' in mode or 'cash' in mode:
                return 1
            elif 'cheque' in mode or 'check' in mode:
                return 2
            elif 'tarjeta' in mode or 'card' in mode:
                return 3  # Default to credit card
    
    # Default: Efectivo (most common in Paraguay)
    return 1


def get_condicion_operacion(sales_invoice):
    """
    Determine SIFEN condicion de operacion (Contado vs Crédito).
    
    SIFEN conditions:
    1 = Contado (Pago inmediato)
    2 = Crédito (Pago diferido)
    
    Args:
        sales_invoice: Sales Invoice document
    
    Returns:
        int: Condicion operacion (1 or 2)
    """
    # Check if invoice has a custom field for condicion
    if hasattr(sales_invoice, 'custom_sifen_condicion') and sales_invoice.custom_sifen_condicion:
        return int(sales_invoice.custom_sifen_condicion)
    
    # Check outstanding amount (if > 0, it's credit)
    if hasattr(sales_invoice, 'outstanding_amount'):
        if sales_invoice.outstanding_amount > 0:
            return 2  # Crédito (tiene saldo pendiente)
        else:
            return 1  # Contado (pagado completamente)
    
    # Check if it's linked to a Sales Order with payment terms
    if hasattr(sales_invoice, 'payment_schedule') and sales_invoice.payment_schedule:
        # Multiple payment schedules = Crédito
        if len(sales_invoice.payment_schedule) > 1:
            return 2  # Crédito
        # Single schedule with future due date = Crédito
        if len(sales_invoice.payment_schedule) == 1:
            due_date = sales_invoice.payment_schedule[0].due_date
            if due_date and due_date > sales_invoice.posting_date:
                return 2  # Crédito
    
    # Check payment terms
    if hasattr(sales_invoice, 'payment_terms_template') and sales_invoice.payment_terms_template:
        # Has payment terms = Crédito
        return 2  # Crédito
    
    # Default: Contado (most common for immediate payment)
    return 1


def get_indicador_presencia(sales_invoice):
    """
    Determine SIFEN presencia indicator based on Sales Invoice data.
    
    SIFEN indicators:
    1 = Operación presencial
    2 = Operación electrónica
    3 = Operación telemarketing
    4 = Venta a domicilio
    5 = Operación bancaria
    6 = Operación cíclica
    9 = Otro
    
    Args:
        sales_invoice: Sales Invoice document
    
    Returns:
        int: Presencia indicator (1-9)
    """
    # Check if invoice has a custom field for presencia
    if hasattr(sales_invoice, 'custom_sifen_presencia') and sales_invoice.custom_sifen_presencia:
        return int(sales_invoice.custom_sifen_presencia)
    
    # Check if it's a POS invoice (point of sale)
    if hasattr(sales_invoice, 'is_pos') and sales_invoice.is_pos:
        return 1  # Operación presencial
    
    # Check if it's from e-commerce or online channel
    if hasattr(sales_invoice, 'source') and sales_invoice.source:
        source_lower = sales_invoice.source.lower()
        if source_lower in ['website', 'e-commerce', 'online', 'web']:
            return 2  # Operación electrónica
    
    # Check sales partner type
    if hasattr(sales_invoice, 'sales_partner') and sales_invoice.sales_partner:
        partner_type = frappe.db.get_value("Sales Partner", sales_invoice.sales_partner, "partner_type")
        if partner_type:
            partner_type_lower = partner_type.lower()
            if 'telemarketing' in partner_type_lower:
                return 3  # Operación telemarketing
            elif 'domicilio' in partner_type_lower or 'home' in partner_type_lower:
                return 4  # Venta a domicilio
    
    # Check if it's a bank operation
    if hasattr(sales_invoice, 'payment_schedule') and sales_invoice.payment_schedule:
        # Bank operations typically have specific payment terms
        # This is a simplified check
        pass
    
    # Default: Presencial (most common case)
    return 1


def get_descuento_global(sales_invoice, moneda):
    """
    Get global discount amount from Sales Invoice.
    
    ERPNext has discounts at item level and invoice level.
    This function calculates the total global discount.
    
    Args:
        sales_invoice: Sales Invoice document
        moneda: Currency code (ISO 4217)
    
    Returns:
        float: Total global discount (0 if no discount)
    """
    # Check if invoice has additional_discount_percentage or discount_amount
    total_discount = 0
    
    # Method 1: Check for additional discount (invoice level)
    if hasattr(sales_invoice, 'discount_amount') and sales_invoice.discount_amount:
        total_discount = float(sales_invoice.discount_amount)
    
    # Method 2: Sum item-level discounts
    # Note: ERPNext stores discount as 'discount_percentage' or 'discount_amount' per item
    # For SIFEN, we need the total discount amount in the invoice currency
    
    # Round according to SIFEN rules
    if moneda == "PYG":
        # For PYG, round to integer (no decimals)
        return round(total_discount)
    else:
        # For other currencies, round to 8 decimals max
        return round(total_discount, 8)


def validar_moneda_sifen(moneda, invoice_name):
    """
    Validate currency against SIFEN allowed currencies.
    
    Args:
        moneda: Currency code (ISO 4217)
        invoice_name: Invoice name for error message
    
    Raises:
        frappe.ValidationError: If currency is not allowed
    """
    # Lista de monedas válidas según SIFEN
    # ISO 4217 codes commonly used in Paraguay
    MONEDAS_VALIDAS = [
        "PYG",  # Guaraní Paraguayo
        "USD",  # Dólar Estadounidense
        "EUR",  # Euro
        "ARS",  # Peso Argentino
        "BRL",  # Real Brasileño
        "CLP",  # Peso Chileno
        "UYU",  # Peso Uruguayo
        "MXN",  # Peso Mexicano
        "COP",  # Peso Colombiano
        "PEN",  # Sol Peruano
        "BOB",  # Boliviano
        "VEF",  # Bolívar Venezolano
        "GBP",  # Libra Esterlina
        "CHF",  # Franco Suizo
        "CAD",  # Dólar Canadiense
        "JPY",  # Yen Japonés
        "CNY",  # Yuan Chino
    ]
    
    if moneda not in MONEDAS_VALIDAS:
        frappe.throw(
            f"Moneda '{moneda}' no permitida para facturación electrónica SIFEN.<br><br>"
            f"<strong>Monedas válidas:</strong> {', '.join(MONEDAS_VALIDAS)}<br><br>"
            f"<strong>Factura:</strong> {invoice_name}",
            title="Moneda No Válida - SIFEN",
            exc=frappe.ValidationError
        )


def prepare_invoice_data(sales_invoice):
    """
    Prepare invoice data in the format required by the Paraguayan SIFEN API.

    Structure:
    {
        "param": { ... },  # Company/Emitter data
        "data": { ... }    # Invoice data
    }
    """
    # Get company information
    company = frappe.get_doc("Company", sales_invoice.company)
    company_ruc = company.tax_id or ""
    
    # Get establishment and expedition point codes
    establecimiento, punto = get_company_and_pos_codes(sales_invoice)
    
    # Get timbrado information
    timbrado = get_timbrado_info(sales_invoice.company)
    
    # Get contributor type
    tipo_contribuyente = get_tipo_contribuyente(sales_invoice.company)
    
    # Get economic activities
    actividades_economicas = get_actividades_economicas(sales_invoice.company)
    
    # Parse invoice number - use invoice.name directly (not naming_series which may have placeholders)
    # Example: "ACC-SINV-2026-00004" → extract "00004"
    _, _, numero = parse_naming_series(sales_invoice.name, sales_invoice.name)
    
    # Format date as ISO 8601
    posting_date = sales_invoice.posting_date
    posting_time = sales_invoice.posting_time if hasattr(sales_invoice, 'posting_time') else None

    # Convert date objects to string for JSON serialization
    if posting_date:
        posting_date_str = str(posting_date)
    else:
        posting_date_str = str(now_datetime().date())
    
    # Format time without microseconds
    posting_time_str = ""
    if posting_time:
        posting_time_str = str(posting_time).split(".")[0]  # Remove microseconds

    fecha = f"{posting_date_str}T{posting_time_str}" if posting_time_str else f"{posting_date_str}T00:00:00"

    # Determine document type based on ERPNext fields
    # SIFEN iTiDE: 1 = Factura, 5 = Nota de Crédito, 6 = Nota de Débito
    if hasattr(sales_invoice, 'is_debit_note') and sales_invoice.is_debit_note:
        tipo_documento = 6  # Nota de Débito
    elif hasattr(sales_invoice, 'is_return') and sales_invoice.is_return:
        tipo_documento = 5  # Nota de Crédito
    else:
        tipo_documento = 1  # Factura

    # Currency and exchange rate
    moneda = sales_invoice.currency or "PYG"
    
    # Validate currency against SIFEN allowed list
    validar_moneda_sifen(moneda, sales_invoice.name)
    
    # Determine exchange rate condition
    # SIFEN D017: 1 = Global, 2 = Por ítem
    # For most cases, use 1 (Global) since ERPNext has single conversion_rate per invoice
    condicion_tipo_cambio = 1  # Global
    
    # Get exchange rate from ERPNext
    cambio = sales_invoice.conversion_rate if hasattr(sales_invoice, 'conversion_rate') and sales_invoice.conversion_rate else 1.0
    
    # SIFEN rules for exchange rate:
    # - If moneda = PYG: NO informar tipo de cambio (cambio no debe enviarse)
    # - If moneda != PYG: Obligatorio informar tipo de cambio real
    if moneda == "PYG":
        # For PYG, set cambio to None (will be excluded from payload)
        # SIFEN requires NOT reporting exchange rate for local currency
        cambio_forzado = None
    else:
        # For foreign currency, use actual conversion rate
        # If conversion_rate is 1.0, use default PYG to USD rate
        if cambio == 1.0:
            cambio_forzado = 6700  # Default PYG to USD rate for SIFEN
        else:
            cambio_forzado = cambio

    # ============================================
    # Build PARAM section (Company/Emitter data)
    # ============================================
    tipo_regimen = get_tipo_regimen(sales_invoice.company)
    param = build_param_section(company, establecimiento, actividades_economicas, timbrado, tipo_contribuyente, tipo_regimen)

    # ============================================
    # Build DATA section (Invoice data)
    # ============================================
    data = build_data_section(
        sales_invoice, company, establecimiento, punto, numero, fecha,
        tipo_documento, moneda, cambio_forzado, tipo_contribuyente, condicion_tipo_cambio
    )

    # Construct final invoice data
    invoice_data = {
        "param": param,
        "data": data
    }

    # Debug: Log full payload to terminal (Python native print)
    import json
    print("\n" + "="*80)
    print("E-INVOICE PAYLOAD - " + sales_invoice.name)
    print("="*80)
    print(json.dumps(invoice_data, indent=2, ensure_ascii=False))
    print("="*80 + "\n")

    # Also log to Frappe Error Log
    frappe.log_error(
        f"Full payload:\nPARAM: {frappe.as_json(param, indent=2)}\n\nDATA.usuario: {frappe.as_json(data.get('usuario'), indent=2)}",
        "E-Invoice: Full Payload Before Send"
    )

    return invoice_data


def map_estado_to_status(estado):
    """
    Map API estado values to E-Invoice Record status options.
    
    API states: encolado, aprobado, rechazado, procesado, etc.
    Record status: Draft, Sent, Received, Processed, Error, Encolado, Aprobado, Rechazado
    """
    if not estado:
        return "Received"
    
    estado_lower = estado.lower()
    
    if estado_lower == "encolado":
        return "Encolado"
    elif estado_lower in ["aprobado", "aceptado"]:
        return "Aprobado"
    elif estado_lower in ["rechazado", "rejectado", "error"]:
        return "Rechazado"
    elif estado_lower == "procesado":
        return "Processed"
    elif estado_lower == "enviado":
        return "Sent"
    elif estado_lower == "recibido":
        return "Received"
    else:
        # Default to Received for unknown states
        return "Received"


def build_param_section(company, establecimiento, actividades_economicas, timbrado, tipo_contribuyente, tipo_regimen):
    """
    Build the 'param' section with company/emitter information.
    """
    # Get company address (first address linked to company)
    address_data = get_company_address(company.name)

    # Get establishment name (denominacion) from Company field
    denominacion = ""
    if hasattr(company, 'sifen_denominacion') and company.sifen_denominacion:
        denominacion = company.sifen_denominacion

    # Get email from company
    email = ""
    if hasattr(company, 'email') and company.email:
        email = company.email
    elif hasattr(company, 'email_id') and company.email_id:
        email = company.email_id

    param = {
        "version": 150,
        "ruc": company.tax_id or "",
        "razonSocial": company.name,
        "nombreFantasia": company.name,
        "actividadesEconomicas": actividades_economicas,
        "timbradoNumero": timbrado.get("numero_timbrado", ""),
        "timbradoFecha": timbrado.get("fecha_timbrado", ""),
        "tipoContribuyente": tipo_contribuyente,
        "tipoRegimen": tipo_regimen,
        "establecimientos": [{
            "codigo": establecimiento,
            "denominacion": denominacion,
            "direccion": address_data.get("address_line1") or "",
            "numeroCasa": address_data.get("sifen_numero_casa") or "1",
            "complementoDireccion1": address_data.get("address_line1") or "",
            "complementoDireccion2": address_data.get("address_line2") or "",
            "departamento": address_data.get("departamento"),
            "departamentoDescripcion": address_data.get("departamentoDescripcion") or "",
            "distrito": address_data.get("distrito"),
            "distritoDescripcion": address_data.get("distritoDescripcion") or "",
            "ciudad": address_data.get("ciudad"),
            "ciudadDescripcion": address_data.get("ciudadDescripcion") or "",
            "telefono": address_data.get("phone") or "",
            "email": address_data.get("email_id") or email
        }]
    }

    return param


def build_data_section(sales_invoice, company, establecimiento, punto, numero, fecha,
                       tipo_documento, moneda, cambio_forzado, tipo_contribuyente, condicion_tipo_cambio):
    """
    Build the 'data' section with invoice information.
    
    Args:
        sales_invoice: Sales Invoice document
        company: Company document
        establecimiento: Establishment code (3 digits)
        punto: Expedition point code (3 digits)
        numero: Invoice number
        fecha: Formatted date
        tipo_documento: SIFEN document type (1=Factura, 5=NC, 6=ND)
        moneda: Currency code (ISO 4217)
        cambio_forzado: Exchange rate (None for PYG, real value for foreign currency)
        tipo_contribuyente: Contributor type
        condicion_tipo_cambio: Exchange rate condition (1=Global, 2=Por ítem)
    """
    # Get customer details
    customer = frappe.db.get_value(
        "Customer",
        sales_invoice.customer,
        ["customer_name", "tax_id", "customer_type", "email_id", "mobile_no", "sifen_contribuyente", "customer_group", "sifen_tipo_documento", "sifen_tipo_impuesto"],
        as_dict=True
    )

    # Get customer's primary address to get country
    address_data = get_customer_address(sales_invoice)
    customer_country = address_data.get("country", "")

    # Get customer address
    address_data = get_customer_address(sales_invoice)

    # Get Paraguay location codes
    location_codes = get_paraguay_location_codes(
        address_data.get("state", ""),
        address_data.get("city", ""),
        address_data.get("country", "")
    )

    # Determine if customer is a contributor
    # Use sifen_contribuyente field if available, otherwise fallback to tax_id check
    es_contribuyente = False
    if customer and customer.sifen_contribuyente is not None:
        es_contribuyente = bool(customer.sifen_contribuyente)
    elif customer and customer.tax_id:
        es_contribuyente = True

    # Get documento_tipo from customer field (sifen_tipo_documento)
    # This field is now required and validated in validar_campos_sifen()
    documento_tipo = 1  # Default: RUC
    
    if customer:
        # First, try to get from sifen_tipo_documento field
        if hasattr(customer, 'sifen_tipo_documento') and customer.sifen_tipo_documento:
            # Extract numeric value from stored format (e.g., "1|RUC" → 1)
            tipo_doc_str = str(customer.sifen_tipo_documento).strip()
            if '|' in tipo_doc_str:
                tipo_doc_str = tipo_doc_str.split('|')[0].strip()
            try:
                documento_tipo = int(tipo_doc_str)
            except (ValueError, TypeError):
                documento_tipo = 1  # Fallback to RUC
        # Fallback: determine from contribuyente status (old logic)
        elif customer.sifen_contribuyente is not None:
            documento_tipo = 1 if customer.sifen_contribuyente else 2
        elif customer.tax_id:
            documento_tipo = 1  # Has RUC, use RUC
        else:
            documento_tipo = 2  # No RUC, use CI
    
    documento_numero = customer.tax_id or sales_invoice.customer

    # Determine tipoOperacion automatically based on customer data
    # Priority order:
    # 1. Foreign country (B2F) - highest priority
    # 2. Government entity in Paraguay (B2G)
    # 3. Company in Paraguay (B2B)
    # 4. Individual in Paraguay (B2C)
    # SIFEN tiposOperaciones: 1=B2B, 2=B2C, 3=B2G, 4=B2F
    # NO default value - must be determined from customer data
    tipo_operacion = None

    if customer:
        # FIRST: Check if customer is foreign (B2F) - this has highest priority
        if customer_country and customer_country != "Paraguay":
            tipo_operacion = 4  # B2F - Business to Foreigner
        
        # SECOND: For Paraguay customers, check customer_type and customer_group
        elif customer.customer_type == "Company":
            # Check if it's a government entity (B2G)
            # Support both Spanish "Gubernamental" and English "Government"
            customer_group_lower = customer.customer_group.lower() if customer.customer_group else ""
            if "gubernamental" in customer_group_lower or "government" in customer_group_lower:
                tipo_operacion = 3  # B2G - Business to Government
            else:
                tipo_operacion = 1  # B2B - Business to Business
        elif customer.customer_type == "Individual":
            # Individual in Paraguay (B2C)
            tipo_operacion = 2  # B2C - Business to Consumer
    
    # Override: If customer has no RUC (tax_id), assume B2C or B2F
    if customer and not customer.tax_id:
        if customer_country and customer_country != "Paraguay":
            tipo_operacion = 4  # B2F - Foreigner without RUC
        else:
            tipo_operacion = 2  # B2C - Consumer final
    
    # Validate tipoOperacion was determined
    if tipo_operacion is None:
        frappe.throw(
            _("Could not determine tipoOperacion for customer {0}.<br><br>"
              "Customer Data:<br>"
              "- customer_type: {1}<br>"
              "- customer_group: {2}<br>"
              "- country: {3}<br>"
              "- tax_id: {4}<br><br>"
              "Please verify customer data is complete.").format(
                sales_invoice.customer,
                customer.customer_type if customer else "N/A",
                customer.customer_group if customer else "N/A",
                customer_country or "N/A",
                customer.tax_id if customer else "N/A"
            ),
            title=_("tipoOperacion Determination Error")
        )

    # Build customer object
    # Note: contribuyente is a boolean (true/false), not integer (1/2)
    # For B2F (foreign customers), departamento/distrito/ciudad are NULL
    # Get country code using ERPNext standard method
    pais_codigo = "PRY"
    pais_nombre = "Paraguay"
    
    if customer_country and customer_country != "Paraguay":
        # Get country code from ERPNext Country doctype (standard method)
        country_code = frappe.db.get_value("Country", customer_country, "code")
        if country_code:
            pais_codigo = country_code.upper()  # ERPNext stores as alpha-2, we need alpha-3
            pais_nombre = customer_country
        
        # If alpha-2 code found, convert to alpha-3 for SIFEN
        alpha2_to_alpha3 = {
            "PY": "PRY", "AR": "ARG", "BR": "BRA", "US": "USA",
            "CL": "CHL", "UY": "URY", "BO": "BOL", "DE": "DEU",
            "ES": "ESP", "MX": "MEX", "CO": "COL", "PE": "PER",
            "EC": "ECU", "JP": "JPN", "KR": "KOR", "IT": "ITA",
            "FR": "FRA", "GB": "GBR", "CA": "CAN", "AU": "AUS",
            "IN": "IND", "RU": "RUS", "CN": "CHN"
        }
        if pais_codigo in alpha2_to_alpha3:
            pais_codigo = alpha2_to_alpha3[pais_codigo]
    
    cliente = {
        "contribuyente": es_contribuyente,  # ✅ Boolean: true/false
        "tipoOperacion": tipo_operacion,  # ✅ Dynamic: 1=B2B, 2=B2C, 3=B2G, 4=B2F
        "ruc": customer.tax_id or "",
        "razonSocial": customer.customer_name or "",
        "nombreFantasia": customer.customer_name or "",
        "direccion": address_data.get("address_line1", "") or "N/A",
        "numeroCasa": address_data.get("sifen_numero_casa") or "0",
        "complementoDireccion1": address_data.get("address_line2", ""),
        # For B2F (tipoOperacion=4), set departamento/distrito/ciudad to None
        "departamento": None if tipo_operacion == 4 else location_codes["departamento"],
        "departamentoDescripcion": None if tipo_operacion == 4 else location_codes["departamentoDescripcion"],
        "distrito": None if tipo_operacion == 4 else location_codes["distrito"],
        "distritoDescripcion": None if tipo_operacion == 4 else location_codes["distritoDescripcion"],
        "ciudad": None if tipo_operacion == 4 else location_codes["ciudad"],
        "ciudadDescripcion": None if tipo_operacion == 4 else location_codes["ciudadDescripcion"],
        # Set country code (PRY for Paraguay, otherwise foreign country code)
        "pais": "PRY" if tipo_operacion != 4 else pais_codigo,
        "paisDescripcion": "Paraguay" if tipo_operacion != 4 else pais_nombre,
        "tipoContribuyente": 1 if customer.customer_type == "Company" else 2,
        "documentoTipo": documento_tipo,
        "documentoNumero": documento_numero,
        # Get telefono from address first, fallback to customer mobile_no
        "telefono": address_data.get("phone") or customer.mobile_no or "",
        "celular": address_data.get("phone") or customer.mobile_no or "",
        # Get email from address first, fallback to customer email_id
        "email": address_data.get("email_id") or customer.email_id or ""
    }
    
    # Build user object (from invoice owner or default)
    usuario = get_usuario_from_invoice(sales_invoice)
    
    # Prepare items data
    items = prepare_items_data(sales_invoice)
    
    # Calculate totals
    total_pago = sales_invoice.grand_total or 0

    # Get control number (generate if not exists)
    if not sales_invoice.custom_numero_control:
        # Generate on the fly if not already assigned (unicidad por compañía)
        from einvoice.e_invoice.utils.api_client import generar_numero_control
        codigo_seguridad = generar_numero_control(sales_invoice.company)
    else:
        codigo_seguridad = sales_invoice.custom_numero_control

    # Get transaction type automatically based on items
    tipo_transaccion = get_tipo_transaccion(sales_invoice)

    # Get description based on document type
    # SIFEN: descripcion = tipo de documento
    if tipo_documento == 5:
        descripcion = "Nota de crédito electrónica"
    elif tipo_documento == 6:
        descripcion = "Nota de débito electrónica"
    else:
        descripcion = "Factura electrónica"

    # Get observation from remarks (ERPNext field)
    # Filter out default ERPNext placeholder text
    observacion = sales_invoice.remarks or ""
    if observacion.lower().strip() in ["no hay observaciones", "sin observaciones", ""]:
        observacion = ""

    # Validate advance payments before sending to SIFEN
    # SIFEN does not allow changing anticipoGlobal from 0 to positive after submission
    validate_anticipo_before_submit(sales_invoice)

    # Get anticipo condition from ERPNext advance payments
    condicion_anticipo = get_condicion_anticipo(sales_invoice)

    # Get advance amount (anticipo global)
    anticipo_global = sales_invoice.total_advance or 0

    # Get global discount amount from ERPNext
    descuento_global = get_descuento_global(sales_invoice, moneda)

    # Get operation condition (Contado vs Crédito)
    condicion_operacion = get_condicion_operacion(sales_invoice)

    # Build condicion.entregas from payments table
    entregas = get_condicion_entregas(sales_invoice, moneda, condicion_tipo_cambio)

    # Get SIFEN tax type from invoice (only the type code, not the rate)
    tipo_impuesto_code, _ = get_sifen_tipo_impuesto(sales_invoice)

    # Build data dictionary
    data = {
        "tipoDocumento": tipo_documento,
        "establecimiento": establecimiento,
        "punto": punto,
        "numero": numero,
        "codigoSeguridadAleatorio": codigo_seguridad,
        "descripcion": descripcion,
        "observacion": observacion,
        "fecha": fecha,
        "tipoEmision": 1,
        "tipoTransaccion": tipo_transaccion,
        "tipoImpuesto": tipo_impuesto_code,  # ✅ Only the code (int), not the tuple
        "moneda": moneda,
        "condicionAnticipo": condicion_anticipo,
        "condicionTipoCambio": condicion_tipo_cambio,
        "descuentoGlobal": descuento_global,
        "anticipoGlobal": anticipo_global,
        "cliente": cliente,
        "usuario": usuario,
        "factura": {
            "presencia": get_indicador_presencia(sales_invoice),
            "fechaEnvio": now_datetime().strftime("%Y-%m-%dT%H:%M:%S")  # Current timestamp when sending
        },
        "condicion": {
            "tipo": condicion_operacion,
            "entregas": entregas  # ✅ Dinámico desde payments[] table
        },
        "items": items,
        "totalPago": total_pago
    }

    # Add credit information if it's a credit operation (tipo = 2)
    if condicion_operacion == 2:
        # Get credit info from payment terms
        credito_info = get_credito_info(sales_invoice)
        data["condicion"]["credito"] = credito_info

    # Add exchange rate only if not PYG (SIFEN rule)
    if moneda != "PYG" and cambio_forzado is not None:
        data["cambio"] = cambio_forzado
    
    return data

def save_received_document(response_data, invoice_name):
    """Save the received document from the external API"""
    
    # Assuming the API returns a PDF document in a 'document' field
    document_content = response_data.get('document')
    document_format = response_data.get('format', 'pdf')
    
    if document_content:
        # Decode base64 content if needed
        import base64
        
        if isinstance(document_content, str):
            try:
                # Try to decode if it's base64
                decoded_content = base64.b64decode(document_content)
            except Exception:
                # If not base64, treat as raw content
                decoded_content = document_content.encode('utf-8')
        else:
            decoded_content = document_content
            
        # Create file in Frappe
        file_name = f"einvoice_{invoice_name}.{document_format}"
        
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": file_name,
            "attached_to_doctype": "Sales Invoice",
            "attached_to_name": invoice_name,
            "content": decoded_content,
            "is_private": 1
        })
        
        file_doc.save()
        
        return file_doc.file_url
    
    return None

def get_invoice_status(factura_id):
    """
    Get invoice status from SIFEN API.
    Endpoint: GET {BASE_URL}/api/invoices/{id}
    
    Args:
        factura_id: The invoice ID returned when creating the invoice
        
    Returns:
        dict: Status information including estado, cdc, correlativo, etc.
    """
    base_url = get_base_url()
    url = f"{base_url}/api/invoices/{factura_id}"
    headers = get_auth_headers()
    
    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "data": result.get("data", {}),
                "message": result.get("message", "Status retrieved successfully")
            }
        else:
            error_message = response.text if response.text else f"HTTP {response.status_code}"
            return {
                "success": False,
                "message": f"Error getting status: {error_message}"
            }
            
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "message": "Request timeout while getting invoice status"
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "message": f"Request error: {str(e)}"
        }
    except Exception as e:
        frappe.log_error(f"E-Invoice Status Error: {str(e)}", "E-Invoice Status Error")
        return {
            "success": False,
            "message": f"Internal error: {str(e)}"
        }


def download_xml(factura_id):
    """
    Download XML document from SIFEN API.
    Endpoint: GET {BASE_URL}/api/invoices/{id}/download-xml
    
    Args:
        factura_id: The invoice ID
        
    Returns:
        dict: Contains xml_content (base64) or file_url if saved
    """
    base_url = get_base_url()
    url = f"{base_url}/api/invoices/{factura_id}/download-xml"
    headers = get_auth_headers()
    
    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            # Save the XML file
            xml_content = response.content
            
            file_name = f"einvoice_{factura_id}.xml"
            file_doc = frappe.get_doc({
                "doctype": "File",
                "file_name": file_name,
                "content": xml_content,
                "is_private": 1
            })
            file_doc.save()
            
            return {
                "success": True,
                "file_url": file_doc.file_url,
                "message": "XML downloaded successfully"
            }
        else:
            error_message = response.text if response.text else f"HTTP {response.status_code}"
            return {
                "success": False,
                "message": f"Error downloading XML: {error_message}"
            }
            
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "message": "Request timeout while downloading XML"
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "message": f"Request error: {str(e)}"
        }
    except Exception as e:
        frappe.log_error(f"E-Invoice XML Download Error: {str(e)}", "E-Invoice XML Download Error")
        return {
            "success": False,
            "message": f"Internal error: {str(e)}"
        }


def download_pdf(factura_id):
    """
    Download PDF (KUDE) document from SIFEN API.
    Endpoint: GET {BASE_URL}/api/invoices/{id}/download-pdf
    
    Args:
        factura_id: The invoice ID
        
    Returns:
        dict: Contains file_url of the downloaded PDF
    """
    base_url = get_base_url()
    url = f"{base_url}/api/invoices/{factura_id}/download-pdf"
    headers = get_auth_headers()
    
    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            # Save the PDF file
            pdf_content = response.content
            
            file_name = f"einvoice_{factura_id}.pdf"
            file_doc = frappe.get_doc({
                "doctype": "File",
                "file_name": file_name,
                "content": pdf_content,
                "is_private": 1
            })
            file_doc.save()
            
            return {
                "success": True,
                "file_url": file_doc.file_url,
                "message": "PDF downloaded successfully"
            }
        else:
            error_message = response.text if response.text else f"HTTP {response.status_code}"
            return {
                "success": False,
                "message": f"Error downloading PDF: {error_message}"
            }
            
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "message": "Request timeout while downloading PDF"
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "message": f"Request error: {str(e)}"
        }
    except Exception as e:
        frappe.log_error(f"E-Invoice PDF Download Error: {str(e)}", "E-Invoice PDF Download Error")
        return {
            "success": False,
            "message": f"Internal error: {str(e)}"
        }


def test_api_connection():
    """Test the connection to the external API"""
    settings = get_einvoice_settings()

    if not settings.enabled:
        return {"success": False, "message": "E-Invoice integration is not enabled"}

    if not settings.api_endpoint:
        return {"success": False, "message": "API endpoint not configured"}

    base_url = get_base_url()
    headers = get_auth_headers()

    try:
        # Try to reach the base endpoint
        response = requests.get(
            base_url,
            headers=headers,
            timeout=settings.request_timeout or 30
        )

        if response.status_code in [200, 401, 403]:
            # 200 = OK, 401/403 means server is reachable but auth might be needed
            return {"success": True, "message": "Connection successful"}
        else:
            return {
                "success": False,
                "message": f"Connection failed: HTTP {response.status_code}"
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"Connection error: {str(e)}"
        }