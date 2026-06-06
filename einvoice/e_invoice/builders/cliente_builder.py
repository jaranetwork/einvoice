"""
Builds the CLIENTE section of SIFEN payload.
Contains customer/supplier information and address.
"""

import frappe
from ..utils.utils import get_paraguay_location_codes


def get_party_details(doc):
    """
    Get party (customer or supplier) details and location codes.
    Works with both Sales Invoice and Purchase Invoice.

    Args:
        doc: Sales Invoice or Purchase Invoice document

    Returns:
        tuple: (party, party_country, address_data, location_codes)
    """
    is_purchase = doc.doctype == "Purchase Invoice"

    if is_purchase:
        party_doctype = "Supplier"
        party_field = "supplier"
        address_field = "supplier_address"
        fields = ["supplier_name", "supplier_name as customer_name", "tax_id", "supplier_type as customer_type",
                  "email_id", "mobile_no", "sifen_contribuyente", "sifen_tipo_contribuyente",
                  "supplier_group as customer_group",
                  "sifen_tipo_documento", "sifen_tipo_impuesto", "sifen_codigo_proveedor as sifen_codigo_cliente",
                  "sifen_tipo_autofactura"]
    else:
        party_doctype = "Customer"
        party_field = "customer"
        address_field = "customer_address"
        fields = ["customer_name", "tax_id", "customer_type", "email_id", "mobile_no",
                  "sifen_contribuyente", "sifen_tipo_contribuyente", "customer_group", "sifen_tipo_documento",
                  "sifen_tipo_impuesto", "sifen_codigo_cliente"]

    party = frappe.db.get_value(
        party_doctype,
        getattr(doc, party_field),
        fields,
        as_dict=True
    )

    address_data = _get_party_address(doc, address_field, party_doctype, getattr(doc, party_field))
    party_country = address_data.get("country", "")

    location_codes = get_paraguay_location_codes(
        address_data.get("state", ""),
        address_data.get("county", ""),  # Distrito
        address_data.get("city", ""),
        address_data.get("country", "")
    )

    return party, party_country, address_data, location_codes


def build_cliente_section(doc, party, address_data, location_codes, tipo_documento):
    """
    Build the 'cliente' section for both Sales Invoice and Purchase Invoice.
    For Purchase Invoice: returns cliente with supplier data (company RUC for Autofactura).
    
    Args:
        doc: Sales Invoice or Purchase Invoice document
        party: Party data dict
        address_data: Address data dict
        location_codes: Location codes dict
        tipo_documento: Document type (5=NC, 6=ND)

    Returns:
        dict: Cliente section for SIFEN payload (supplier data for Purchase Invoice)
    """
    return _build_cliente_original(party, address_data, location_codes, doc)


def build_auto_factura_section(doc, party, address_data, location_codes):
    """
    Build the 'autoFactura' section for Purchase Invoice.
    
    Args:
        doc: Purchase Invoice document
        party: Supplier data dict
        address_data: Address data dict
        location_codes: Location codes dict
    
    Returns:
        dict: autoFactura section for SIFEN payload
    """
    # Check if this is a Purchase Invoice (autofactura)
    if doc.doctype != "Purchase Invoice":
        return None
    
    # Determine tipoVendedor (tipo de operación)
    tipo_vendedor = 1  # Default: No contribuyente
    if party.get('sifen_tipo_autofactura'):
        tipo_vendedor_raw = str(party.get('sifen_tipo_autofactura')).split('|')[0].strip()
        try:
            tipo_vendedor = int(tipo_vendedor_raw)
        except (ValueError, TypeError):
            tipo_vendedor = 1
    
    # Determine if supplier is contributor
    es_contribuyente = _determine_contribuyente(party)
    
    # Get tipoContribuyente from SIFEN field
    tipo_contribuyente_raw = party.get('sifen_tipo_contribuyente', '')
    if tipo_contribuyente_raw:
        tipo_contribuyente_str = str(tipo_contribuyente_raw).split('|')[0].strip()
        try:
            tipo_contribuyente = int(tipo_contribuyente_str)
        except (ValueError, TypeError):
            tipo_contribuyente = 1 if party.supplier_type == "Individual" else 2
    else:
        tipo_contribuyente = 1 if party.supplier_type == "Individual" else 2
    
    # Get documentoTipo from supplier
    documento_tipo = None
    if party.get('sifen_tipo_documento'):
        tipo_doc_str = str(party.get('sifen_tipo_documento')).strip()
        if '|' in tipo_doc_str:
            tipo_doc_str = tipo_doc_str.split('|')[0].strip()
        try:
            documento_tipo = int(tipo_doc_str)
        except (ValueError, TypeError):
            documento_tipo = 1
    
    # documentoNumero is typically the tax_id/RUC
    documento_numero = party.tax_id or ""
    
    # nombre uses alias customer_name (supplier_name aliased to customer_name in get_party_details)
    nombre_party = party.customer_name
    
    # Get transaction location codes (same as party location for now)
    transaccion_codes = location_codes.copy()
    
    # Get tipoVendedor from supplier sifen_tipo_autofactura field, default to 1
    tipo_vendedor = 1  # Default: No contribuyente
    if party.get('sifen_tipo_autofactura'):
        tipo_vendedor_str = str(party.get('sifen_tipo_autofactura')).split('|')[0].strip()
        try:
            tipo_vendedor = int(tipo_vendedor_str)
        except (ValueError, TypeError):
            tipo_vendedor = 1
    
    # Build autoFactura section
    auto_factura = {
        "tipoVendedor": tipo_vendedor,
        "documentoTipo": documento_tipo,
        "documentoNumero": documento_numero,
        "nombre": nombre_party,
        "direccion": address_data.get("address_line1", ""),
        "numeroCasa": address_data.get("sifen_numero_casa", ""),
        "departamento": location_codes.get("departamento"),
        "departamentoDescripcion": location_codes.get("departamentoDescripcion"),
        "distrito": location_codes.get("distrito"),
        "distritoDescripcion": location_codes.get("distritoDescripcion"),
        "ciudad": location_codes.get("ciudad"),
        "ciudadDescripcion": location_codes.get("ciudadDescripcion"),
        "ubicacion": {
            "lugar": address_data.get("address_line1", ""),
            "departamento": transaccion_codes.get("departamento"),
            "departamentoDescripcion": transaccion_codes.get("departamentoDescripcion"),
            "distrito": transaccion_codes.get("distrito"),
            "distritoDescripcion": transaccion_codes.get("distritoDescripcion"),
            "ciudad": transaccion_codes.get("ciudad"),
            "ciudadDescripcion": transaccion_codes.get("ciudadDescripcion")
        }
    }
    
    return auto_factura


def _build_cliente_original(party, address_data, location_codes, doc=None):
    """
    Build the original 'cliente' section for Sales Invoice.
    For Purchase Invoice: uses company RUC instead of supplier RUC (Autofactura rule).
    
    Args:
        party: Customer data dict
        address_data: Address data dict
        location_codes: Location codes dict
        doc: Document object (optional, for Purchase Invoice RUC override)
    
    Returns:
        dict: Cliente section for SIFEN payload
    """
    # Determine operation type
    tipo_operacion = _determine_tipo_operacion(party, address_data.get("country", ""))

    # Determine if contributor
    es_contribuyente = _determine_contribuyente(party)

    # Determine tipoContribuyente from SIFEN custom field only — no fallback
    tipo_contribuyente = None
    tipo_contribuyente_raw = party.get('sifen_tipo_contribuyente', '')
    if tipo_contribuyente_raw:
        try:
            code = str(tipo_contribuyente_raw).split('|')[0].strip()
            tipo_contribuyente = int(code)
        except (ValueError, TypeError, IndexError):
            pass

    # Get country codes
    pais_codigo, pais_nombre = _get_pais_data(tipo_operacion, address_data.get("country", ""))

    # Get document type and number (only if not contributor and not B2F)
    documento_tipo, documento_numero = _get_documento_data(party, party.customer_name, es_contribuyente, tipo_operacion)

    # For Purchase Invoice, use company RUC instead of supplier RUC (Autofactura rule)
    ruc = party.tax_id
    if doc and doc.doctype == "Purchase Invoice":
        company = frappe.get_doc("Company", doc.company)
        ruc = company.tax_id

    # Build cliente object
    cliente = {
        "contribuyente": es_contribuyente,
        "tipoOperacion": tipo_operacion,
        "razonSocial": party.customer_name,
        "nombreFantasia": party.customer_name,
        "direccion": address_data.get("address_line1", ""),
        "numeroCasa": address_data.get("sifen_numero_casa"),
        "complementoDireccion1": address_data.get("address_line2", ""),
        "departamento": None if tipo_operacion == 4 else location_codes["departamento"],
        "departamentoDescripcion": None if tipo_operacion == 4 else location_codes["departamentoDescripcion"],
        "distrito": None if tipo_operacion == 4 else location_codes["distrito"],
        "distritoDescripcion": None if tipo_operacion == 4 else location_codes["distritoDescripcion"],
        "ciudad": None if tipo_operacion == 4 else location_codes["ciudad"],
        "ciudadDescripcion": None if tipo_operacion == 4 else location_codes["ciudadDescripcion"],
        "pais": "PRY" if tipo_operacion != 4 else pais_codigo,
        "paisDescripcion": "Paraguay" if tipo_operacion != 4 else pais_nombre,
        "telefono": address_data.get("phone") or party.mobile_no,
        "celular": address_data.get("phone") or party.mobile_no,
        "email": address_data.get("email_id") or party.email_id,
        "codigo": party.sifen_codigo_cliente
    }

    # Only add tipoContribuyente when set (no fallback guessing)
    if tipo_contribuyente is not None:
        cliente["tipoContribuyente"] = tipo_contribuyente

    # Only add RUC when customer is a SIFEN contributor
    if es_contribuyente:
        cliente["ruc"] = ruc

    # Only add document type/number if not contributor and not B2F
    if documento_tipo is not None and documento_numero is not None:
        cliente["documentoTipo"] = documento_tipo
        cliente["documentoNumero"] = documento_numero

    return cliente


def _get_party_address(doc, address_field, party_doctype=None, party_name=None):
    """Get party address from invoice or party master."""
    address_data = {
        "address_line1": "",
        "address_line2": "",
        "city": "",
        "county": "",
        "state": "",
        "country": "Paraguay",
        "phone": "",
        "email_id": "",
        "sifen_numero_casa": ""
    }

    # Try to get from invoice address
    invoice_address = getattr(doc, address_field, None) if hasattr(doc, address_field) else None
    if invoice_address:
        try:
            address_doc = frappe.get_doc("Address", invoice_address)
            address_data.update({
                "address_line1": address_doc.address_line1,
                "address_line2": address_doc.address_line2,
                "city": address_doc.city,
                "county": address_doc.county,
                "state": address_doc.state,
                "country": address_doc.country,
                "phone": address_doc.phone,
                "email_id": address_doc.email_id,
                "sifen_numero_casa": getattr(address_doc, 'sifen_numero_casa', '')
            })
            return address_data
        except Exception:
            pass

    # Fallback to party master address if no address found on invoice
    if not party_name:
        return address_data

    try:
        # Method 1: Query Address table directly, filtering by is_primary_address and Dynamic Link
        primary_address_name = frappe.db.sql("""
            SELECT ad.name 
            FROM `tabAddress` ad
            INNER JOIN `tabDynamic Link` dl ON dl.parent = ad.name
            WHERE dl.link_doctype = %s 
              AND dl.link_name = %s 
              AND dl.parenttype = 'Address'
              AND ad.is_primary_address = 1
            LIMIT 1
        """, (party_doctype, party_name), as_dict=True)

        primary_address_name = primary_address_name[0].name if primary_address_name else None

        # Method 2: Any address linked to the party (no primary filter)
        if not primary_address_name:
            any_address = frappe.db.sql("""
                SELECT ad.name 
                FROM `tabAddress` ad
                INNER JOIN `tabDynamic Link` dl ON dl.parent = ad.name
                WHERE dl.link_doctype = %s 
                  AND dl.link_name = %s 
                  AND dl.parenttype = 'Address'
                LIMIT 1
            """, (party_doctype, party_name), as_dict=True)

            primary_address_name = any_address[0].name if any_address else None

        # Method 3: Query Address by address_title containing party name
        if not primary_address_name:
            address_title = frappe.db.get_value(
                "Address",
                {"address_title": ["like", f"%{party_name}%"]},
                "name"
            )
            primary_address_name = address_title

        # Load the address document
        if primary_address_name:
            address_doc = frappe.get_doc("Address", primary_address_name)
            address_data.update({
                "address_line1": address_doc.address_line1,
                "address_line2": address_doc.address_line2,
                "city": address_doc.city,
                "county": address_doc.county,
                "state": address_doc.state,
                "country": address_doc.country,
                "phone": address_doc.phone,
                "email_id": address_doc.email_id,
                "sifen_numero_casa": getattr(address_doc, 'sifen_numero_casa', '')
            })
    except Exception:
        pass

    return address_data


def _determine_tipo_operacion(customer, customer_country):
    """Determine operation type based on customer data."""
    if not customer:
        return 2  # Default to B2C
    
    # Foreign customer
    if customer_country and customer_country != "Paraguay":
        return 4  # B2F
    
    # Company customer
    customer_type = customer.get('customer_type') if isinstance(customer, dict) else customer.customer_type
    customer_group = customer.get('customer_group') if isinstance(customer, dict) else customer.customer_group
    
    if customer_type == "Company":
        customer_group_lower = (customer_group or "").lower()
        if "gubernamental" in customer_group_lower or "government" in customer_group_lower:
            return 3  # B2G
        return 1  # B2B
    
    # Individual customer
    return 2  # B2C


def _determine_contribuyente(customer):
    """Determine if customer is contributor."""
    if customer and customer.sifen_contribuyente is not None:
        return bool(customer.sifen_contribuyente)
    elif customer and customer.tax_id:
        return True
    return False


def _get_documento_data(customer, customer_name, es_contribuyente, tipo_operacion):
    """
    Get document type and number.
    Only returns values if customer is NOT contributor and operation is not B2F (4).
    """
    # Only document type/number for non-contributors and non-B2F operations
    if es_contribuyente or tipo_operacion == 4:
        return None, None

    documento_tipo = None
    documento_numero = customer.tax_id or customer_name if customer else customer_name

    if customer and customer.sifen_tipo_documento:
        tipo_doc_str = str(customer.sifen_tipo_documento).strip()
        if '|' in tipo_doc_str:
            tipo_doc_str = tipo_doc_str.split('|')[0].strip()
        try:
            documento_tipo = int(tipo_doc_str)
        except (ValueError, TypeError):
            documento_tipo = None

    return documento_tipo, documento_numero


def _get_pais_data(tipo_operacion, customer_country):
    """Get country code and name."""
    from ..utils.utils import get_country_codes

    if tipo_operacion != 4:
        return "PRY", "Paraguay"
    
    if not customer_country:
        return "PRY", "Paraguay"
    
    # Get country codes
    alpha2_to_alpha3 = {
        "PY": "PRY", "AR": "ARG", "BR": "BRA", "US": "USA",
        "CL": "CHL", "UY": "URY", "BO": "BOL", "DE": "DEU",
        "ES": "ESP", "MX": "MEX", "CO": "COL", "PE": "PER",
        "EC": "ECU", "JP": "JPN", "KR": "KOR", "IT": "ITA",
        "FR": "FRA", "GB": "GBR", "CA": "CAN", "AU": "AUS",
        "IN": "IND", "RU": "RUS", "CN": "CHN"
    }
    
    country_code = frappe.db.get_value("Country", customer_country, "code")
    
    if country_code:
        pais_codigo = country_code.upper()
        pais_nombre = customer_country
        
        if pais_codigo in alpha2_to_alpha3:
            pais_codigo = alpha2_to_alpha3[pais_codigo]
        
        return pais_codigo, pais_nombre
    
    return "PRY", customer_country or "Paraguay"
