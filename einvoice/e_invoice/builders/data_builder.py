"""
Builds the DATA section of SIFEN payload.
Main orchestrator for data section construction.
"""

import frappe
from frappe.utils import now_datetime
from ..helpers import (
    get_descuento_global,
    validar_moneda_sifen,
    get_sifen_tipo_impuesto
)
from ..utils.utils import (
    get_tipo_transaccion,
    get_indicador_presencia,
    get_condicion_anticipo,
    get_condicion_operacion,
    get_condicion_entregas,
)
from .param_builder import build_param_section
from .cliente_builder import build_cliente_section
from .items_builder import build_items_data
from .condicion_builder import build_condicion_section


def build_data_section(sales_invoice, company, establecimiento, punto, numero, fecha=None,
                       tipo_documento=None, moneda=None, cambio_forzado=None, 
                       tipo_contribuyente=None, condicion_tipo_cambio=None):
    """
    Build the 'data' section with invoice information.
    
    Args:
        sales_invoice: Sales Invoice document
        company: Company document
        establecimiento: Establishment code
        punto: Expedition point code
        numero: Invoice number
        fecha: Formatted date (optional)
        tipo_documento: SIFEN document type (optional)
        moneda: Currency code (optional)
        cambio_forzado: Exchange rate (optional)
        tipo_contribuyente: Contributor type (optional)
        condicion_tipo_cambio: Exchange rate condition (optional)
    
    Returns:
        dict: Data section for SIFEN payload
    """
    # Get customer details
    from .cliente_builder import get_customer_details
    customer, customer_country, address_data, location_codes = get_customer_details(sales_invoice)
    
    # Set defaults
    moneda = moneda or sales_invoice.currency or "PYG"
    condicion_tipo_cambio = condicion_tipo_cambio or 1
    
    # Validate currency
    validar_moneda_sifen(moneda, sales_invoice.name)
    
    # Determine document type if not provided
    if tipo_documento is None:
        tipo_documento = _determine_document_type(sales_invoice)
    
    # Build date if not provided
    if fecha is None:
        fecha = _build_fecha(sales_invoice)
    
    # Build sections
    cliente = build_cliente_section(sales_invoice, customer, address_data, location_codes, tipo_documento)
    items = build_items_data(sales_invoice, moneda)
    condicion = build_condicion_section(sales_invoice, moneda, condicion_tipo_cambio)
    
    # Get other values
    usuario = _build_usuario(sales_invoice)
    factura = _build_factura_metadata(sales_invoice)
    
    # Calculate totals
    total_pago = sales_invoice.grand_total or 0
    
    # Get control number
    codigo_seguridad = sales_invoice.custom_numero_control or ""
    
    # Get transaction type
    tipo_transaccion = get_tipo_transaccion(sales_invoice)
    
    # Get description
    descripcion = _get_documento_descripcion(tipo_documento)
    
    # Get observation
    observacion = _get_observacion(sales_invoice)
    
    # Build notaCreditoDebito section
    nota_credito_debito = _build_nota_credito_debito(sales_invoice, tipo_documento)
    
    # Build documentoAsociado section
    documento_asociado = _build_documento_asociado(sales_invoice, tipo_documento)
    
    # Get advance and discount
    anticipo_global = sales_invoice.total_advance or 0
    descuento_global = get_descuento_global(sales_invoice, moneda)
    
    # Get operation condition
    condicion_operacion = get_condicion_operacion(sales_invoice)
    
    # Get tax type
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
        "tipoImpuesto": tipo_impuesto_code,
        "moneda": moneda,
        "condicionAnticipo": get_condicion_anticipo(sales_invoice),
        "condicionTipoCambio": condicion_tipo_cambio,
        "descuentoGlobal": descuento_global,
        "anticipoGlobal": anticipo_global,
        "cliente": cliente,
        "usuario": usuario,
        "factura": factura,
        "condicion": condicion,
        "items": items,
        "totalPago": total_pago
    }
    
    # Add notaCreditoDebito section if applicable
    if nota_credito_debito:
        data["notaCreditoDebito"] = nota_credito_debito
    
    # Add documentoAsociado section if applicable
    if documento_asociado:
        data["documentoAsociado"] = documento_asociado
    
    # Add credit information if credit operation
    if condicion_operacion == 2:
        data["condicion"]["credito"] = _get_credito_info(sales_invoice)
    
    # Add exchange rate if not PYG
    if moneda != "PYG" and cambio_forzado is not None:
        data["cambio"] = cambio_forzado
    
    return data


def _determine_document_type(sales_invoice):
    """Determine document type based on invoice fields."""
    if hasattr(sales_invoice, 'is_return') and sales_invoice.is_return:
        return 5  # Nota de Crédito
    elif hasattr(sales_invoice, 'is_debit_note') and sales_invoice.is_debit_note:
        return 6  # Nota de Débito
    else:
        return 1  # Factura


def _build_fecha(sales_invoice):
    """Build fecha string from posting date and time."""
    posting_date = sales_invoice.posting_date
    posting_time = getattr(sales_invoice, 'posting_time', None)
    
    if posting_date:
        posting_date_str = str(posting_date)
    else:
        posting_date_str = str(now_datetime().date())
    
    if posting_time:
        posting_time_str = str(posting_time).split(".")[0]
        return f"{posting_date_str}T{posting_time_str}"
    else:
        return f"{posting_date_str}T00:00:00"


def _build_usuario(sales_invoice):
    """Build usuario section from invoice owner."""
    from ..utils.utils import get_usuario_from_invoice
    return get_usuario_from_invoice(sales_invoice)


def _build_factura_metadata(sales_invoice):
    """Build factura metadata section."""
    return {
        "presencia": get_indicador_presencia(sales_invoice),
        "fechaEnvio": now_datetime().strftime("%Y-%m-%dT%H:%M:%S")
    }


def _get_documento_descripcion(tipo_documento):
    """Get document description based on type."""
    if tipo_documento == 5:
        return "Nota de crédito electrónica"
    elif tipo_documento == 6:
        return "Nota de débito electrónica"
    else:
        return "Factura electrónica"


def _get_observacion(sales_invoice):
    """Get observation from remarks field."""
    observacion = sales_invoice.remarks or ""
    if observacion.lower().strip() in ["no hay observaciones", "sin observaciones", ""]:
        return ""
    return observacion


def _build_nota_credito_debito(sales_invoice, tipo_documento):
    """Build notaCreditoDebito section for NC/ND."""
    if tipo_documento not in [5, 6]:
        return {}
    
    motivo = getattr(sales_invoice, 'sifen_motivo_nota_credito_debito', '')
    
    if motivo:
        motivo_code = str(motivo).split("|")[0].strip() if "|" in str(motivo) else str(motivo).strip()
        try:
            return {"motivo": int(motivo_code)}
        except (ValueError, TypeError):
            pass
    
    return {}


def _build_documento_asociado(sales_invoice, tipo_documento):
    """Build documentoAsociado section for NC/ND."""
    if tipo_documento not in [5, 6]:
        return []

    cdc_original = ""

    # Try to get CDC from original invoice
    if hasattr(sales_invoice, 'return_against') and sales_invoice.return_against:
        try:
            original_invoice = frappe.get_doc("Sales Invoice", sales_invoice.return_against)
            cdc_original = original_invoice.custom_sifen_cdc or ""
        except Exception:
            pass

    if cdc_original:
        return [{"formato": 1, "cdc": cdc_original}]

    return []


def _get_credito_info(sales_invoice):
    """Get credit information from payment terms."""
    from ..utils.utils import get_credito_info
    return get_credito_info(sales_invoice)


def prepare_invoice_data(sales_invoice):
    """
    Prepare complete invoice data for SIFEN API.
    Orchestrates all builders.

    Args:
        sales_invoice: Sales Invoice document

    Returns:
        dict: Complete payload for SIFEN API
    """
    # Get company and parse invoice number
    company = frappe.get_doc("Company", sales_invoice.company)
    establecimiento, punto, numero = _parse_invoice_number(sales_invoice)

    # Build sections
    param = build_param_section(company, establecimiento)
    data = build_data_section(sales_invoice, company, establecimiento, punto, numero)

    return {"param": param, "data": data}


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
