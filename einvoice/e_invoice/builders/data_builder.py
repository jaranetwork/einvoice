"""
Builds the DATA section of SIFEN payload.
Main orchestrator for data section construction.
"""

import frappe
from frappe.utils import now_datetime, formatdate, format_datetime
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

    # Build sections - build_cliente_section now returns cliente OR autoFactura based on doctype
    items = build_items_data(doc, moneda)
    # Skip condition section for Delivery Note (no payment terms)
    if doc.doctype == "Delivery Note":
        condicion = {}
    else:
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
    
    if doc.doctype != "Delivery Note":
      # Get observation
      observacion = _get_observacion(doc)
      # Get advance and discount
      anticipo_global = doc.total_advance
      descuento_global = get_descuento_global(doc, moneda)

    # Build notaCreditoDebito section
    nota_credito_debito = _build_nota_credito_debito(doc, tipo_documento)

    # Build documentoAsociado section
    documento_asociado = _build_documento_asociado(doc, tipo_documento)    

    # Get operation condition
    condicion_operacion = get_condicion_operacion(doc)

    # Get tax type
    tipo_impuesto_code, _ = get_sifen_tipo_impuesto(doc)
    
    # Build cliente section (supplier data for Purchase Invoice, customer data for Sales Invoice)
    cliente_section = build_cliente_section(doc, party, address_data, location_codes, tipo_documento)
    
    # Determine if Purchase Invoice
    is_purchase = doc.doctype == "Purchase Invoice"
    
    # Build autoFactura section for Purchase Invoice
    from .cliente_builder import build_auto_factura_section
    auto_factura_section = build_auto_factura_section(doc, party, address_data, location_codes) if is_purchase else None
    
    # Build data dictionary - both doctypes use "cliente" key
    data = {
        "tipoDocumento": tipo_documento,
        "establecimiento": establecimiento,
        "punto": punto,
        "numero": numero,
        "codigoSeguridadAleatorio": codigo_seguridad,
        "descripcion": descripcion,
        "fecha": fecha,
        "tipoEmision": _get_tipo_emision(doc),
        "tipoTransaccion": _get_tipo_transaccion(doc),
        "tipoImpuesto": tipo_impuesto_code,
        "moneda": moneda,
        "cliente": cliente_section,
        "usuario": usuario,
        "factura": factura,
        "condicion": condicion,
        "items": items,
        "totalPago": total_pago
    }

    if doc.doctype != "Delivery Note":
        data["observacion"] = observacion
        # Add descuentoGlobal section if applicable
        if descuento_global > 0:
            data["descuentoGlobal"] = descuento_global
    else:
        remision = {
            "motivo": _get_motivo_remision(doc),
            "tipoResponsable": _extract_code_from_select(doc.delivery_note_responsable) if hasattr(doc, 'delivery_note_responsable') and doc.delivery_note_responsable else None,
            "kms": _get_kms_from_delivery_note(doc),
            "fechaFactura": formatdate(doc.posting_date, "yyyy-mm-dd") if hasattr(doc, 'posting_date') and doc.posting_date else None
        }
        # Remove None values
        remision = {k: v for k, v in remision.items() if v is not None}
        # Add remision section to data
        data["remision"] = remision
        
        # Add transporte section for Delivery Note
        transporte = _build_transporte_section(doc)
        if transporte:
            data["transporte"] = transporte
    # Add cliente section - for Purchase Invoice, also include autoFactura
    if is_purchase:
        data["cliente"] = cliente_section
        data["autoFactura"] = auto_factura_section
    else:
        data["cliente"] = cliente_section

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
    # Purchase Invoice = Autofactura (tipoDocumento = 4)
    if doc.doctype == "Purchase Invoice":
        if hasattr(doc, 'is_return') and doc.is_return:
            return 5  # Nota de Crédito Autofactura
        elif hasattr(doc, 'is_debit_note') and doc.is_debit_note:
            return 6  # Nota de Débito Autofactura
        else:
            return 4  # Autofactura electrónica
    
    # Delivery Note (tipoDocumento = 7)
    elif doc.doctype == "Delivery Note":
        if hasattr(doc, 'is_return') and doc.is_return:
            # Note: Delivery Note returns are rare, but if they exist, they would be type 8
            # For now, we'll treat them as regular delivery notes
            return 7  # Nota de remisión electrónica
        else:
            return 7  # Nota de remisión electrónica
    
    # Sales Invoice
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
    # Autofactura types (Purchase Invoice)
    if tipo_documento == 4:
        return "Autofactura electrónica"
    elif tipo_documento == 7:
        return "Nota de remisión electrónica"
    elif tipo_documento == 8:
        return "Comprobante de retención electrónico"
    # Sales Invoice types
    elif tipo_documento == 5:
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
    """
    Build documentoAsociado section.
    For Sales Invoice (formato 1): busca CDC en return_against
    For Purchase Invoice (formato 3): constanciaTipo, constanciaNumero, constanciaControl
    """
    # Purchase Invoice always needs documentoAsociado
    if doc.doctype == "Purchase Invoice":
        constancia_tipo = 1
        constancia_numero = None
        constancia_control = None

        if doc.supplier:
            supplier_data = frappe.db.get_value(
                "Supplier",
                doc.supplier,
                ["sifen_tipo_constancias", "supplier_constancia_numero", "supplier_constancia_control"],
                as_dict=True
            )
            if supplier_data:
                if supplier_data.sifen_tipo_constancias:
                    constancia_tipo = int(str(supplier_data.sifen_tipo_constancias).split('|')[0].strip())
                constancia_numero = supplier_data.supplier_constancia_numero
                constancia_control = supplier_data.supplier_constancia_control

        return [{"formato": 3, "constanciaTipo": constancia_tipo, "constanciaNumero": constancia_numero, "constanciaControl": constancia_control}]

    # Delivery Note: link to associated Sales Invoice
    if doc.doctype == "Delivery Note":
        cdc_original = ""
        si_name = None
        if hasattr(doc, 'items') and doc.items:
            si_name = doc.items[0].against_sales_invoice
        if si_name:
            try:
                si_cdc = frappe.db.get_value("Sales Invoice", si_name, "custom_sifen_cdc")
                if si_cdc:
                    cdc_original = si_cdc
            except Exception:
                pass
        if cdc_original:
            return [{"formato": 1, "cdc": cdc_original}]
        return []

    # Sales Invoice: only for NC/ND (tipo 5, 6)
    if tipo_documento not in [5, 6]:
        return []

    cdc_original = ""

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

def _get_motivo_remision(doc):
    motivo_remision_raw = getattr(doc, 'delivery_note_motivo', '')
    if motivo_remision_raw:
        motivo_remision_str = str(motivo_remision_raw).split('|')[0].strip()
        try:
            return int(motivo_remision_str)
        except (ValueError, TypeError):
            pass
    return None


def _extract_code_from_select(value):
    """Extract numeric code from a Frappe select field value (format: 'code|Label')."""
    if value and '|' in str(value):
        code_str = str(value).split('|')[0].strip()
        try:
            return int(code_str)
        except (ValueError, TypeError):
            return code_str
    return value


def _get_kms_from_delivery_note(doc):
    """
    Get kilometers from linked Delivery Trip via Delivery Note's delivery stops.
    Traverses: Delivery Note → Delivery Stop → Delivery Trip
    """
    try:
        # Get all Delivery Stops linked to this Delivery Note
        delivery_stops = frappe.get_all(
            "Delivery Stop",
            filters={"delivery_note": doc.name},
            fields=["parent"]
        )
        
        if not delivery_stops:
            return None
            
        # Get unique parent Delivery Trip names
        trip_names = list(set([stop.parent for stop in delivery_stops if stop.parent]))
        
        if not trip_names:
            return None
            
        # Get kms from the first Delivery Trip that has it
        for trip_name in trip_names:
            trip_kms = frappe.db.get_value("Delivery Trip", trip_name, "delivery_trip_kms")
            if trip_kms is not None and trip_kms != "":
                try:
                    return float(trip_kms)
                except (ValueError, TypeError):
                    continue
                    
        return None
    except Exception:
        return None


def _build_transporte_section(doc):
    """
    Build transporte section for Delivery Note.
    Extracts data from linked Delivery Trip via Delivery Stops.
    """
    try:
        # Get Delivery Stops for this Delivery Note
        delivery_stops = frappe.get_all(
            "Delivery Stop",
            filters={"delivery_note": doc.name},
            fields=["parent", "estimated_arrival"],
            order_by="estimated_arrival desc"
        )
        
        if not delivery_stops:
            return None
        
        # Get unique Delivery Trip names (first stop's parent is the main trip)
        trip_name = delivery_stops[0].parent if delivery_stops[0].parent else None
        if not trip_name:
            return None
        
        # Get Delivery Trip fields
        trip_fields = ["delivery_trip_tipo", "delivery_trip_modalidad", "departure_time", "vehicle", "delivery_trip_resp_flete"]
        trip_data = frappe.db.get_value("Delivery Trip", trip_name, trip_fields, as_dict=True)
        
        if not trip_data:
            return None
        
        # Build transporte dictionary
        transporte = {}
        
        # tipo (from delivery_trip_tipo select field)
        if trip_data.get("delivery_trip_tipo"):
            tipo_code = _extract_code_from_select(trip_data.delivery_trip_tipo)
            if tipo_code:
                transporte["tipo"] = tipo_code
        
        # modalidad (from delivery_trip_modalidad select field)
        if trip_data.get("delivery_trip_modalidad"):
            modalidad_code = _extract_code_from_select(trip_data.delivery_trip_modalidad)
            if modalidad_code:
                transporte["modalidad"] = modalidad_code
        
        # tipoResponsable (from delivery_trip_resp_flete select field)
        if trip_data.get("delivery_trip_resp_flete"):
            resp_code = _extract_code_from_select(trip_data.delivery_trip_resp_flete)
            if resp_code:
                transporte["tipoResponsable"] = resp_code
        
        # inicioEstimadoTranslado (format: YYYY-MM-DD HH:MM)
        if trip_data.get("departure_time"):
            transporte["inicioEstimadoTranslado"] = format_datetime(trip_data.departure_time, "yyyy-mm-dd HH:MM")
        
        # finEstimadoTranslado - get latest estimated_arrival from stops
        if delivery_stops and delivery_stops[0].get("estimated_arrival"):
            transporte["finEstimadoTranslado"] = format_datetime(delivery_stops[0].estimated_arrival, "yyyy-mm-dd HH:MM")
        
        # salida: company address from Delivery Note
        salida = _build_address_block(getattr(doc, 'company_address', None))
        if salida:
            transporte["salida"] = salida
        
        # entrega: customer billing address from Delivery Note
        entrega = _build_address_block(getattr(doc, 'customer_address', None))
        if entrega:
            transporte["entrega"] = entrega
        
        # vehiculo: from linked Vehicle on Delivery Trip
        vehiculo = _build_vehiculo_block(trip_data)
        if vehiculo:
            transporte["vehiculo"] = vehiculo
        
        # condicionNegociacion: Incoterm from linked Shipment
        condicion = _build_condicion_negociacion(doc)
        if condicion:
            transporte["condicionNegociacion"] = condicion
        
        # transportista: carrier from Linked Supplier (doc.transporter)
        transportista = _build_transportista_block(doc)
        if transportista:
            transporte["transportista"] = transportista
        
        return transporte if transporte else None
        
    except Exception:
        return None


def _build_vehiculo_block(trip_data):
    """Build vehiculo block for transporte section from Delivery Trip vehicle data."""
    vehicle_name = trip_data.get("vehicle")
    if not vehicle_name:
        return None

    try:
        vehicle = frappe.get_doc("Vehicle", vehicle_name)
    except Exception:
        return None

    tipo = getattr(vehicle, 'sifen_vehiculo_tipo', None)
    if not tipo:
        return None

    vehiculo = {
        "tipo": tipo,
        "marca": (vehicle.make or "")[:10],
    }

    doc_tipo_raw = getattr(vehicle, 'sifen_documento_tipo', None)
    if doc_tipo_raw:
        doc_tipo_code = _extract_code_from_select(doc_tipo_raw)
        if doc_tipo_code == 1:
            vehiculo["documentoTipo"] = 1
            if vehicle.chassis_no:
                vehiculo["documentoNumero"] = vehicle.chassis_no
        elif doc_tipo_code == 2:
            vehiculo["documentoTipo"] = 2
            if vehicle.chassis_no:
                vehiculo["numeroMatricula"] = vehicle.chassis_no

    return vehiculo


def _build_condicion_negociacion(doc):
    """Get Incoterm code from Shipment linked to this Delivery Note."""
    try:
        shipment_links = frappe.get_all(
            "Shipment Delivery Note",
            filters={"delivery_note": doc.name},
            fields=["parent"],
            limit=1
        )
        if not shipment_links:
            return None
        shipment_name = shipment_links[0].parent
        incoterm_name = frappe.db.get_value("Shipment", shipment_name, "incoterm")
        if not incoterm_name:
            return None
        return frappe.db.get_value("Incoterm", incoterm_name, "code")
    except Exception:
        return None


def _build_transportista_block(doc):
    """
    Build transportista block for Delivery Note.
    Only built when doc.transporter (Link to Supplier) is set.
    Chofer data from linked Driver using license_number as documentoNumero.
    """
    if not doc.get("transporter"):
        return None

    try:
        supplier = frappe.get_doc("Supplier", doc.transporter)
    except Exception:
        return None

    contribuyente = bool(supplier.sifen_contribuyente)
    transportista = {
        "contribuyente": contribuyente,
        "nombre": supplier.supplier_name or "",
        "direccion": _get_supplier_primary_address(doc.transporter) or "",
        "pais": "PRY",
    }

    if contribuyente:
        if supplier.tax_id:
            transportista["ruc"] = supplier.tax_id
    else:
        tipo_raw = supplier.sifen_tipo_documento
        if tipo_raw:
            try:
                transportista["documentoTipo"] = int(str(tipo_raw).split('|')[0].strip())
            except Exception:
                pass
        transportista["documentoNumero"] = supplier.tax_id or ""

    if doc.get("driver"):
        try:
            driver = frappe.get_doc("Driver", doc.driver)
            chofer = {
                "nombre": driver.full_name or "",
                "documentoNumero": driver.license_number or "",
            }
            if driver.address:
                addr = frappe.db.get_value("Address", driver.address, "address_line1")
                if addr:
                    chofer["direccion"] = addr
            transportista["chofer"] = chofer
        except Exception:
            return None

    return transportista if transportista.get("chofer") else None


def _get_supplier_primary_address(supplier_name):
    """Get primary address line for a Supplier."""
    try:
        linked = frappe.db.get_all(
            "Dynamic Link",
            filters={"link_doctype": "Supplier", "link_name": supplier_name, "parenttype": "Address"},
            fields=["parent"],
            limit=20
        )
        if not linked:
            return None
        addr_names = [l.parent for l in linked]
        # Prefer primary address
        primary = frappe.db.get_value(
            "Address",
            {"name": ["in", addr_names], "is_primary_address": 1},
            "address_line1"
        )
        if primary:
            return primary
        # Fallback: first linked address
        return frappe.db.get_value("Address", addr_names[0], "address_line1")
    except Exception:
        pass
    return None


def _build_address_block(address_name):
    """Build address block for transporte.salida/entrega from an Address document."""
    if not address_name:
        return None

    try:
        address = frappe.get_doc("Address", address_name)
    except Exception:
        return None

    from ..utils.utils import get_paraguay_location_codes
    location_codes = get_paraguay_location_codes(
        address.state or "",
        address.county or "",
        address.city or "",
        address.country or "Paraguay"
    )

    return {
        "direccion": address.address_line1 or "",
        "numeroCasa": getattr(address, 'sifen_numero_casa', '') or "",
        "complementoDireccion1": address.address_line2 or "",
        "complementoDireccion2": "",
        "departamento": location_codes.get("departamento"),
        "departamentoDescripcion": location_codes.get("departamentoDescripcion"),
        "distrito": location_codes.get("distrito"),
        "distritoDescripcion": location_codes.get("distritoDescripcion"),
        "ciudad": location_codes.get("ciudad"),
        "ciudadDescripcion": location_codes.get("ciudadDescripcion"),
        "pais": "PRY",
        "paisDescripcion": "Paraguay",
        "telefonoContacto": address.phone or ""
    }
