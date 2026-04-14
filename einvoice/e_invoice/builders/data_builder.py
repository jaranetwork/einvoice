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
    get_indicador_presencia,
    get_condicion_anticipo,
    get_condicion_operacion,
    get_condicion_entregas,
)
from .param_builder import build_param_section
from .cliente_builder import build_cliente_section
from .items_builder import build_items_data
from .condicion_builder import build_condicion_section


def build_data_section(doc, company, establecimiento, punto, numero, fecha=None,
                       tipo_documento=None, moneda=None, cambio_forzado=None,
                       tipo_contribuyente=None, condicion_tipo_cambio=None):
    """
    Build the 'data' section with invoice information.
    Works with both Sales Invoice and Purchase Invoice.

    Args:
        doc: Sales Invoice or Purchase Invoice document
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
    # Get party (customer/supplier) details
    from .cliente_builder import get_party_details
    party, party_country, address_data, location_codes = get_party_details(doc)
    
    # Set defaults
    moneda = moneda or doc.currency
    condicion_tipo_cambio = condicion_tipo_cambio

    # Validate currency
    validar_moneda_sifen(moneda, doc.name)

    # Determine document type if not provided
    if tipo_documento is None:
        tipo_documento = _determine_document_type(doc)

    # Build date if not provided
    if fecha is None:
        fecha = _build_fecha(doc)

    # Build sections
    cliente = build_cliente_section(doc, party, address_data, location_codes, tipo_documento)
    items = build_items_data(doc, moneda)
    condicion = build_condicion_section(doc, moneda, condicion_tipo_cambio)

    # Get other values
    usuario = _build_usuario(doc)
    factura = _build_factura_metadata(doc)

    # Calculate totals
    total_pago = doc.grand_total

    # Get control number
    codigo_seguridad = doc.custom_numero_control

    # Get description
    descripcion = _get_documento_descripcion(tipo_documento)

    # Get observation
    observacion = _get_observacion(doc)

    # Build notaCreditoDebito section
    nota_credito_debito = _build_nota_credito_debito(doc, tipo_documento)

    # Build documentoAsociado section
    documento_asociado = _build_documento_asociado(doc, tipo_documento)

    # Get advance and discount
    anticipo_global = doc.total_advance
    descuento_global = get_descuento_global(doc, moneda)

    # Get operation condition
    condicion_operacion = get_condicion_operacion(doc)

    # Get tax type
    tipo_impuesto_code, _ = get_sifen_tipo_impuesto(doc)
    
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
        "tipoEmision": _get_tipo_emision(doc),
        "tipoTransaccion": _get_tipo_transaccion(doc),
        "tipoImpuesto": tipo_impuesto_code,
        "moneda": moneda,
        "cliente": cliente,
        "usuario": usuario,
        "factura": factura,
        "condicion": condicion,
        "items": items,
        "totalPago": total_pago
    }

    # Add descuentoGlobal section if applicable
    if descuento_global > 0:
        data["descuentoGlobal"] = descuento_global

    # Add condicionAnticipo and anticipoGlobal section if applicable
    if get_condicion_anticipo(doc) is not None:
        data["condicionAnticipo"] = get_condicion_anticipo(doc)
        data["anticipoGlobal"] = anticipo_global

    # Add notaCreditoDebito section if applicable
    if nota_credito_debito:
        data["notaCreditoDebito"] = nota_credito_debito

    # Add documentoAsociado section if applicable
    if documento_asociado:
        data["documentoAsociado"] = documento_asociado
        
    # Add credit information if credit operation
    if condicion_operacion == 2:
        data["condicion"]["credito"] = _get_credito_info(doc)

    # Add exchange rate if not PYG
    if moneda != "PYG":
        data["condicionTipoCambio"] = 1  # 1 = Tipo de cambio global
        # Get from Currency Exchange first
        cambio_valor = frappe.db.get_value(
            "Currency Exchange",
            {"from_currency": moneda, "to_currency": "PYG"},
            "exchange_rate"
        )
        
        # Fallback to conversion_rate from doc
        if not cambio_valor and hasattr(doc, 'conversion_rate') and doc.conversion_rate:
            cambio_valor = doc.conversion_rate
        
        if cambio_valor:
            data["cambio"] = float(cambio_valor)

    return data


def _determine_document_type(doc):
    """Determine document type based on invoice fields."""
    if hasattr(doc, 'is_return') and doc.is_return:
        return 5  # Nota de Crédito
    elif hasattr(doc, 'is_debit_note') and doc.is_debit_note:
        return 6  # Nota de Débito
    else:
        return 1  # Factura


def _build_fecha(doc):
    """Build fecha string from posting date and time."""
    posting_date = doc.posting_date
    posting_time = getattr(doc, 'posting_time', None)
    
    if posting_date:
        posting_date_str = str(posting_date)
    else:
        posting_date_str = str(now_datetime().date())
    
    if posting_time:
        posting_time_str = str(posting_time).split(".")[0]
        return f"{posting_date_str}T{posting_time_str}"
    else:
        return f"{posting_date_str}T00:00:00"


def _build_usuario(doc):
    """Build usuario section from invoice owner."""
    from ..utils.utils import get_usuario_from_invoice
    return get_usuario_from_invoice(doc)


def _build_factura_metadata(doc):
    """Build factura metadata section."""
    return {
        "presencia": get_indicador_presencia(doc),
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


def _get_observacion(doc):
    """Get observation from remarks field."""
    observacion = doc.remarks or ""
    if observacion.lower().strip() in ["no hay observaciones", "sin observaciones", ""]:
        return ""
    return observacion


def _build_nota_credito_debito(doc, tipo_documento):
    """Build notaCreditoDebito section for NC/ND."""
    if tipo_documento not in [5, 6]:
        return {}

    motivo = getattr(doc, 'sifen_motivo_nota_credito_debito', '')
    
    if motivo:
        motivo_code = str(motivo).split("|")[0].strip() if "|" in str(motivo) else str(motivo).strip()
        try:
            return {"motivo": int(motivo_code)}
        except (ValueError, TypeError):
            pass
    
    return {}


def _build_documento_asociado(doc, tipo_documento):
    """Build documentoAsociado section for NC/ND."""
    if tipo_documento not in [5, 6]:
        return []

    cdc_original = ""

    # Try to get CDC from original invoice
    if hasattr(doc, 'return_against') and doc.return_against:
        try:
            original_doctype = doc.doctype
            original_invoice = frappe.get_doc(original_doctype, doc.return_against)
            cdc_original = original_invoice.custom_sifen_cdc
        except Exception:
            pass

    if cdc_original:
        return [{"formato": 1, "cdc": cdc_original}]

    return []


def _get_credito_info(doc):
    """Get credit information from payment terms."""
    from ..utils.utils import get_credito_info
    return get_credito_info(doc)


def prepare_invoice_data(doc):
    """
    Prepare complete invoice data for SIFEN API.
    Orchestrates all builders.
    Works with both Sales Invoice and Purchase Invoice.

    Args:
        doc: Sales Invoice or Purchase Invoice document

    Returns:
        dict: Complete payload for SIFEN API
    """
    # Get company and parse invoice number
    company = frappe.get_doc("Company", doc.company)
    establecimiento, punto, numero = _parse_invoice_number(doc)

    # Build sections
    param = build_param_section(company, establecimiento)
    data = build_data_section(doc, company, establecimiento, punto, numero)

    return {"param": param, "data": data}


def _parse_invoice_number(doc):
    """Parse invoice number to extract establishment, point and number."""
    invoice_name = doc.name

    # Get Company data first (used for all invoice types)
    company = None
    if hasattr(doc, 'company') and doc.company:
        try:
            company = frappe.get_doc("Company", doc.company)
        except Exception:
            pass

    # For POS invoices, get expedition point code from POS Profile
    if hasattr(doc, 'is_pos') and doc.is_pos:
        if hasattr(doc, 'pos_profile') and doc.pos_profile:
            try:
                pos_profile = frappe.get_doc("POS Profile", doc.pos_profile)
                if hasattr(pos_profile, 'codigo_punto_expedicion') and pos_profile.codigo_punto_expedicion:
                    punto = pos_profile.codigo_punto_expedicion.zfill(3)[-3:]
                    # Get establishment code from Company
                    est = "001"
                    if company and hasattr(company, 'codigo_establecimiento') and company.codigo_establecimiento:
                        est = company.codigo_establecimiento.zfill(3)[-3:]
                    numero = invoice_name.rsplit('-', 1)[-1]
                    return est, punto, numero
            except Exception:
                pass

    # For non-POS invoices, get expedition point from Company default
    if company:
        if hasattr(company, 'codigo_punto_expedicion_default') and company.codigo_punto_expedicion_default:
            punto = company.codigo_punto_expedicion_default.zfill(3)[-3:]
            # Get establishment code from Company
            est = "001"
            if hasattr(company, 'codigo_establecimiento') and company.codigo_establecimiento:
                est = company.codigo_establecimiento.zfill(3)[-3:]
            numero = invoice_name.rsplit('-', 1)[-1]
            return est, punto, numero


def _get_tipo_emision(doc):
    """
    Get tipo de emisión from E-Invoice Setting.
    1 = Normal, 2 = Contingencia (when system cannot connect to SIFEN).
    Defaults to 1 (Normal) if not configured.
    """
    try:
        settings = frappe.get_single("E-Invoice Setting")
        if hasattr(settings, 'tipo_emision') and settings.tipo_emision:
            return int(str(settings.tipo_emision).split('|')[0].strip())
    except Exception:
        pass
    return 1  # Default to Normal


def _get_tipo_transaccion(doc):
    """
    Get tipo de transacción from document field (manual selection).
    Returns None if not set.
    """
    tipo_transaccion_raw = getattr(doc, 'sifen_tipo_transaccion', '')
    if tipo_transaccion_raw:
        tipo_transaccion_str = str(tipo_transaccion_raw).split('|')[0].strip()
        try:
            return int(tipo_transaccion_str)
        except (ValueError, TypeError):
            pass
    return None
    
