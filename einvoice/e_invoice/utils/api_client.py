"""
E-Invoice API Client - Refactored Version
Main orchestrator for SIFEN e-invoicing operations.

This module coordinates validators, builders, and API communication.
"""

import frappe
import json
import requests
import base64
from frappe import _
from frappe.utils import now_datetime, escape_html

# Import validators
from ..validators import (
    validate_company_sifen_fields,
    validate_customer_sifen_fields,
    validate_items_sifen_fields,
    validate_payment_sifen_fields
)

# Import helpers
from ..helpers import (
    generar_numero_control,
    asignar_numero_control,
    validar_moneda_sifen,
    get_descuento_global
)

# Constants
SIFEN_API_TIMEOUT = 30


def test_api_connection():
    """
    Test connection to SIFEN API.
    
    Returns:
        dict: {success: bool, message: str}
    """
    settings = frappe.get_single("E-Invoice Setting")
    
    if not settings.enabled:
        return {"success": False, "message": "E-Invoice integration is not enabled"}
    
    if not settings.api_endpoint:
        return {"success": False, "message": "API Endpoint is not configured"}
    
    if not settings.api_key:
        return {"success": False, "message": "API Key is not configured"}
    
    # Try to make a test request
    try:
        base_url = settings.api_endpoint.rstrip('/')
        url = f"{base_url}/api/health"  # Health check endpoint
        
        headers = {
            "Authorization": f"Bearer {settings.api_key}"
        }
        
        response = requests.get(url, headers=headers, timeout=SIFEN_API_TIMEOUT)
        
        if response.status_code == 200:
            return {"success": True, "message": "Successfully connected to SIFEN API"}
        else:
            return {"success": False, "message": f"API returned status code: {response.status_code}"}
    
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Request timeout. SIFEN API took too long to respond."}
    except requests.exceptions.ConnectionError:
        return {"success": False, "message": "Cannot connect to SIFEN API. Please check the API Endpoint URL."}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


def get_invoice_status(factura_id):
    """
    Get invoice status from SIFEN API.
    
    Args:
        factura_id: SIFEN factura ID
    
    Returns:
        dict: {success: bool, data: dict or None, message: str}
    """
    settings = frappe.get_single("E-Invoice Setting")
    
    if not settings.enabled:
        return {"success": False, "message": "E-Invoice integration is not enabled"}
    
    if not settings.api_endpoint:
        return {"success": False, "message": "API Endpoint is not configured"}
    
    if not settings.api_key:
        return {"success": False, "message": "API Key is not configured"}
    
    if not factura_id:
        return {"success": False, "message": "Factura ID is required"}
    
    try:
        base_url = settings.api_endpoint.rstrip('/')
        url = f"{base_url}/api/invoices/{factura_id}"
        
        headers = {
            "Authorization": f"Bearer {settings.api_key}"
        }
        
        response = requests.get(url, headers=headers, timeout=SIFEN_API_TIMEOUT)
        
        if response.status_code == 200:
            result = response.json()
            return {"success": True, "data": result.get("data", {})}
        elif response.status_code == 404:
            return {"success": False, "message": "Invoice not found in SIFEN API"}
        else:
            return {"success": False, "message": f"API returned status code: {response.status_code}"}
    
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Request timeout"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "message": "Cannot connect to SIFEN API"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


# ============================================================================
# MAIN ORCHESTRATOR FUNCTIONS
# ============================================================================

def validar_campos_sifen(doc, method=None):
    """
    Validate all SIFEN required fields before sending invoice.
    Orchestrates all validators.

    Detects document type and delegates to appropriate validator.

    Args:
        doc: Sales Invoice or Purchase Invoice document
        method: Event method name (unused)

    Raises:
        frappe.ValidationError: If validation fails
    """
    doctype = doc.doctype

    if doctype == "Purchase Invoice":
        # Delegate to Purchase Invoice validator
        from einvoice.e_invoice.doc_events.purchase_invoice import validate_invoice_for_einvoice
        validate_invoice_for_einvoice(doc)
        return

    # Sales Invoice validation (original logic)
    errors = []

    # Get company document
    try:
        company = frappe.get_doc("Company", doc.company)
    except Exception:
        errors.append(_("Company {0} not found").format(doc.company))
        frappe.throw("<br><br>".join(errors), title=_("Validation Error"))

    # Validate Company fields
    company_errors = validate_company_sifen_fields(doc, company)
    errors.extend(company_errors)

    # Validate Customer fields
    customer_data, customer_country = _get_customer_data(doc)
    tipo_operacion = _get_tipo_operacion(customer_data, customer_country)

    customer_errors = validate_customer_sifen_fields(
        doc, customer_data, customer_country, tipo_operacion
    )
    errors.extend(customer_errors)

    # Validate Items
    items_errors = validate_items_sifen_fields(doc, customer_country)
    errors.extend(items_errors)

    if doctype == "Sales Invoice":
      # Validate Payments (only during on_submit, not during validate/save)
      # Payment validation is now handled by validate_payment_sifen_fields in payment_validator.py
      if hasattr(doc, 'docstatus') and doc.docstatus == 1:
          # Validate payment fields for normal invoices
          is_pos_invoice = hasattr(doc, 'is_pos') and doc.is_pos
          payment_errors = validate_payment_sifen_fields(doc, is_pos_invoice, customer_country)
          errors.extend(payment_errors)

    # Validate Control Number
    control_errors = _validate_control_number(doc)
    errors.extend(control_errors)

    # Raise all errors
    if errors:
        frappe.throw("<br><br>".join(errors), title=_("Missing Required Fields for E-Invoice"))


def send_invoice_to_external_api(doc):
    """
    Send invoice to SIFEN API.
    Works with both Sales Invoice and Purchase Invoice.

    Args:
        doc: Sales Invoice or Purchase Invoice document

    Returns:
        dict: API response
    """
    # Import here to avoid circular import
    from ..builders import prepare_invoice_data

    # Prepare invoice data
    invoice_data = prepare_invoice_data(doc)

    # Save JSON to document BEFORE sending (works for both Sales Invoice and Purchase Invoice)
    json_str = json.dumps(invoice_data, indent=2, ensure_ascii=False)
    try:
        frappe.db.set_value(
            doc.doctype,
            doc.name,
            "custom_einvoice_json",
            json_str
        )
        frappe.db.commit()
    except Exception as e:
        print(f"Warning: Could not save JSON to document: {e}")

    # Log the complete payload to console for debugging (visible in bench start)
    print("\n" + "="*80)
    print(f"E-INVOICE PAYLOAD FOR {doc}")
    print("="*80)
    print(json_str)
    print("="*80 + "\n")

    # Get API settings
    settings = frappe.get_single("E-Invoice Setting")
    base_url = settings.api_endpoint.rstrip('/')
    url = f"{base_url}/api/facturar/crear"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.api_key}"
    }

    # Log request details to console
    print("\n" + "="*80)
    print(f"E-INVOICE REQUEST FOR {doc.name}")
    print("="*80)
    print(f"URL: {url}")
    print(f"Headers: {headers}")
    print("="*80 + "\n")

    # Send to API
    try:
        response = requests.post(
            url,
            json=invoice_data,
            headers=headers,
            timeout=SIFEN_API_TIMEOUT
        )

        return _process_api_response(response, doc, invoice_data)

    except requests.exceptions.Timeout:
        return {"success": False, "message": "Request timeout while connecting to SIFEN API"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"Request error: {str(e)[:100]}"}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_customer_data(doc):
    """Get customer data and country."""
    customer_data = frappe.db.get_value(
        "Customer",
        doc.customer,
        ["customer_type", "customer_group", "tax_id", 
         "sifen_contribuyente", "sifen_tipo_documento", 
         "sifen_tipo_impuesto"],
        as_dict=True
    )
    
    customer_country = ""
    if doc.customer_address:
        address_data = frappe.db.get_value(
            "Address",
            doc.customer_address,
            ["country"],
            as_dict=True
        )
        if address_data:
            customer_country = address_data.country or ""
    
    return customer_data, customer_country


def _get_tipo_operacion(customer_data, customer_country):
    """Determine operation type."""
    if not customer_data:
        return None
    
    if customer_country and customer_country != "Paraguay":
        return 4  # B2F
    
    if customer_data.customer_type == "Company":
        customer_group_lower = (customer_data.customer_group or "").lower()
        if "gubernamental" in customer_group_lower or "government" in customer_group_lower:
            return 3  # B2G
        return 1  # B2B
    
    return 2  # B2C


def _is_pos_invoice(doc):
    """Check if invoice is POS."""
    if hasattr(doc, 'is_pos') and doc.is_pos:
        return True
    if hasattr(doc, 'pos_profile') and doc.pos_profile:
        return True
    return False


def _validate_control_number(doc):
    """Validate control number."""
    errors = []
    
    if doc.custom_numero_control:
        if len(str(doc.custom_numero_control)) != 9:
            errors.append(_("Control Number must have exactly 9 digits"))
        if not str(doc.custom_numero_control).isdigit():
            errors.append(_("Control Number must contain only digits"))
    
    return errors


def _parse_invoice_number(sales_invoice):
    """Parse invoice number to extract establishment, point and number."""
    invoice_name = sales_invoice.name
    last_hyphen_idx = invoice_name.rfind('-')
    
    if last_hyphen_idx != -1 and last_hyphen_idx < len(invoice_name) - 1:
        numero = invoice_name[last_hyphen_idx + 1:]
        if len(numero) > 8:
            numero = numero[-8:]
        
        remaining = invoice_name[:last_hyphen_idx]
        parts = remaining.split('-')
        
        if len(parts) >= 2:
            est = parts[-2].zfill(3)[-3:] if parts[-2].isdigit() else "001"
            punto = parts[-1].zfill(3)[-3:] if parts[-1].isdigit() else "001"
            return est, punto, numero
    
    return "001", "001", invoice_name[-8:] if len(invoice_name) > 8 else invoice_name


def _process_api_response(response, doc, invoice_data):
    """Process API response and update invoice."""
    try:
        result = response.json()
    except json.JSONDecodeError:
        return {
            "success": False,
            "message": f"Invalid JSON response from API: {response.text[:200]}"
        }
    
    if result.get("success") is True:
        return _handle_api_success(result, doc, invoice_data)
    else:
        return _handle_api_failure(result, response)


def _handle_api_success(result, doc, invoice_data):
    """Handle successful API response."""
    from frappe.utils import now_datetime

    data = result.get("data", {})
    factura_id = data.get("facturaId", "")

    update_dict = {
        "custom_sifen_factura_id": factura_id,
        "custom_einvoice_generated": 1,
        "custom_einvoice_generated_date": now_datetime(),
        "custom_sifen_correlativo": data.get("correlativo", "") or "",
        "custom_sifen_estado": data.get("estado", "") or "",
    }
    cdc = data.get("cdc")
    if cdc:
        update_dict["custom_sifen_cdc"] = cdc

    frappe.db.set_value(doc.doctype, doc.name, update_dict)
    frappe.db.commit()

    # Format message
    formatted_message = _format_success_message(data, result.get("message", ""))

    return {
        "success": True,
        "message": formatted_message,
        "data": data
    }


def _handle_api_failure(result, response):
    """Handle failed API response."""
    error_message = result.get("message", "Unknown error")
    error_detail = result.get("error", "")
    full_error = f"{error_message} {error_detail}".strip()
    
    frappe.log_error(
        f"E-Invoice API Error: {full_error[:100]}",
        "E-Invoice API Error"
    )
    
    return {
        "success": False,
        "message": full_error or f"API returned failure (HTTP {response.status_code})"
    }


def _format_success_message(data, base_message):
    """Format success message for user."""
    html_lines = [
        '<div style="padding: 15px; background: #f8f9fa; border-radius: 5px; border: 1px solid #dee2e6;">',
        '<h4 style="margin-top: 0; margin-bottom: 15px; color: #28a745; font-size: 16px;">✓ E-Invoice Generated Successfully</h4>'
    ]
    
    if base_message:
        html_lines.append(f'<p style="margin: 10px 0; color: #6c757d;"><strong>Message:</strong> {escape_html(base_message)}</p>')
    
    html_lines.append('<table style="width: 100%; border-collapse: collapse; margin-top: 10px;">')
    
    if data.get("facturaId"):
        html_lines.append(f'<tr><td style="padding: 10px 8px; border-bottom: 1px solid #dee2e6; font-weight: 600;">Factura ID:</td>'
                         f'<td style="padding: 10px 8px; border-bottom: 1px solid #dee2e6;">{escape_html(str(data.get("facturaId")))}</td></tr>')
    
    if data.get("estado"):
        status_color = "#28a745" if str(data.get("estado")).lower() in ["aprobado", "aceptado", "encolado"] else "#ffc107"
        html_lines.append(f'<tr><td style="padding: 10px 8px; border-bottom: 1px solid #dee2e6; font-weight: 600;">Estado:</td>'
                         f'<td style="padding: 10px 8px; border-bottom: 1px solid #dee2e6; color: {status_color}; font-weight: 700;">{escape_html(str(data.get("estado")))}</td></tr>')
    
    html_lines.append('</table></div>')
    
    return ''.join(html_lines)


# ============================================================================
# FILE DOWNLOAD FUNCTIONS
# ============================================================================

@frappe.whitelist()
def download_sifen_file(factura_id, file_type, invoice_name=None):
    """
    Download XML or KUDE file from SIFEN API.
    
    Args:
        factura_id: SIFEN factura ID
        file_type: 'xml' or 'kude'
        invoice_name: Sales Invoice name for filename
    
    Returns:
        dict: File content and metadata
    """
    # Validate settings
    settings = frappe.get_single("E-Invoice Setting")
    
    if not settings.enabled:
        frappe.throw(_("E-Invoice integration is not enabled"), title=_("E-Invoice Not Enabled"))
    
    if not settings.api_endpoint:
        frappe.throw(_("API Endpoint is not configured"), title=_("API Endpoint Missing"))
    
    if not settings.api_key:
        frappe.throw(_("API Key is not configured"), title=_("API Key Missing"))
    
    if not factura_id:
        frappe.throw(_("Factura ID is required"))
    
    # Build URL
    base_url = settings.api_endpoint.rstrip('/')
    
    if file_type == 'xml':
        url = f"{base_url}/api/invoices/{factura_id}/download-xml"
        filename = f"{invoice_name or factura_id}.xml"
        content_type = "application/xml"
    elif file_type == 'kude':
        url = f"{base_url}/api/invoices/{factura_id}/download-pdf"
        filename = f"{invoice_name or factura_id}_KUDE.pdf"
        content_type = "application/pdf"
    else:
        frappe.throw(_("Invalid file type. Must be 'xml' or 'kude'"))
    
    # Make API request
    headers = {
        "Authorization": f"Bearer {settings.api_key}",
        "Accept": content_type
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=SIFEN_API_TIMEOUT)
        
        if response.status_code == 200:
            file_content = base64.b64encode(response.content).decode('utf-8')
            return {
                "file_content": file_content,
                "filename": filename,
                "content_type": content_type
            }
        elif response.status_code == 401:
            frappe.throw(_("Authentication failed. API Key is invalid or expired"), title=_("Authentication Error"))
        elif response.status_code == 404:
            frappe.throw(_("File not found in SIFEN API"), title=_("File Not Found"))
        else:
            frappe.throw(_("Failed to download file: HTTP {0}").format(response.status_code))
    
    except requests.exceptions.Timeout:
        frappe.throw(_("Request timeout. SIFEN API took too long to respond"))
    except requests.exceptions.ConnectionError:
        frappe.throw(_("Cannot connect to SIFEN API. Please check your internet connection"))


@frappe.whitelist()
def download_xml(factura_id, invoice_name=None):
    """
    Download XML file from SIFEN API.
    Wrapper for download_sifen_file with file_type='xml'.

    Args:
        factura_id: SIFEN factura ID
        invoice_name: Sales Invoice name for filename

    Returns:
        dict: File content and metadata
    """
    return download_sifen_file(factura_id, 'xml', invoice_name)


@frappe.whitelist()
def download_pdf(factura_id, invoice_name=None):
    """
    Download PDF (KUDE) file from SIFEN API.
    Wrapper for download_sifen_file with file_type='kude'.

    Args:
        factura_id: SIFEN factura ID
        invoice_name: Sales Invoice name for filename

    Returns:
        dict: File content and metadata
    """
    return download_sifen_file(factura_id, 'kude', invoice_name)


# ============================================================================
# BACKGROUND STATUS CHECK
# ============================================================================

def check_invoice_status_background(invoice_name, factura_id, user, doctype="Sales Invoice"):
    """
    Background job to periodically check invoice status from SIFEN API
    and notify the user via realtime when status changes.

    Args:
        invoice_name: Invoice/Note name
        factura_id: SIFEN factura ID
        user: Frappe user to notify
        doctype: DocType name (default: Sales Invoice)
    """
    import time

    max_attempts = 30
    last_estado = ""

    for attempt in range(max_attempts):
        time.sleep(10)

        try:
            result = get_invoice_status(factura_id)
        except Exception:
            continue

        if not result.get("success"):
            continue

        data = result.get("data", {})
        estado = data.get("estado", "")

        if not estado or estado == last_estado:
            continue

        last_estado = estado

        update_dict = {
            "custom_sifen_estado": estado,
            "custom_sifen_correlativo": data.get("correlativo", "") or "",
        }
        cdc = data.get("cdc")
        if cdc:
            update_dict["custom_sifen_cdc"] = cdc

        try:
            frappe.db.set_value(doctype, invoice_name, update_dict)
            frappe.db.commit()
        except Exception:
            continue

        # Get invoice fields for realtime update
        try:
            inv = frappe.db.get_value(
                doctype, invoice_name,
                ["custom_einvoice_generated_date", "custom_sifen_factura_id"],
                as_dict=True
            )
            generated_date = inv.custom_einvoice_generated_date if inv else ""
            current_factura_id = inv.custom_sifen_factura_id if inv else factura_id
        except Exception:
            generated_date = ""
            current_factura_id = factura_id

        event_data = {
            "invoice_name": invoice_name,
            "doctype": doctype,
            "estado": estado,
            "factura_id": current_factura_id,
            "cdc": data.get("cdc") or "",
            "correlativo": data.get("correlativo") or "",
            "generated_date": str(generated_date or ""),
        }

        frappe.publish_realtime("sifen_status_update", event_data, user=user)

        if estado in ("Aceptado", "Rechazado"):
            frappe.publish_realtime("sifen_status_final", event_data, user=user)
            break
