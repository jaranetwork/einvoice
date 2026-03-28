"""
Builds the CLIENTE section of SIFEN payload.
Contains customer information and address.
"""

import frappe
from ..utils.utils import get_paraguay_location_codes


def get_customer_details(sales_invoice):
    """
    Get customer details and location codes.
    
    Args:
        sales_invoice: Sales Invoice document
    
    Returns:
        tuple: (customer, customer_country, address_data, location_codes)
    """
    customer = frappe.db.get_value(
        "Customer",
        sales_invoice.customer,
        ["customer_name", "tax_id", "customer_type", "email_id", "mobile_no",
         "sifen_contribuyente", "customer_group", "sifen_tipo_documento",
         "sifen_tipo_impuesto", "sifen_codigo_cliente"],
        as_dict=True
    )
    
    address_data = _get_customer_address(sales_invoice)
    customer_country = address_data.get("country", "")

    location_codes = get_paraguay_location_codes(
        address_data.get("state", ""),
        address_data.get("county", ""),  # Distrito
        address_data.get("city", ""),
        address_data.get("country", "")
    )

    return customer, customer_country, address_data, location_codes


def build_cliente_section(sales_invoice, customer, address_data, location_codes, tipo_documento):
    """
    Build the 'cliente' section with customer information.
    
    Args:
        sales_invoice: Sales Invoice document
        customer: Customer data dict
        address_data: Address data dict
        location_codes: Location codes dict
        tipo_documento: Document type (5=NC, 6=ND)
    
    Returns:
        dict: Cliente section for SIFEN payload
    """
    # Determine operation type
    tipo_operacion = _determine_tipo_operacion(customer, address_data.get("country", ""))
    
    # Determine if contributor
    es_contribuyente = _determine_contribuyente(customer)
    
    # Get document type and number
    documento_tipo, documento_numero = _get_documento_data(customer, sales_invoice.customer)
    
    # Get country codes
    pais_codigo, pais_nombre = _get_pais_data(tipo_operacion, address_data.get("country", ""))
    
    # Build cliente object
    cliente = {
        "contribuyente": es_contribuyente,
        "tipoOperacion": tipo_operacion,
        "ruc": customer.tax_id or "",
        "razonSocial": customer.customer_name or "",
        "nombreFantasia": customer.customer_name or "",
        "direccion": address_data.get("address_line1", "") or "N/A",
        "numeroCasa": address_data.get("sifen_numero_casa") or "0",
        "complementoDireccion1": address_data.get("address_line2", ""),
        "departamento": None if tipo_operacion == 4 else location_codes["departamento"],
        "departamentoDescripcion": None if tipo_operacion == 4 else location_codes["departamentoDescripcion"],
        "distrito": None if tipo_operacion == 4 else location_codes["distrito"],
        "distritoDescripcion": None if tipo_operacion == 4 else location_codes["distritoDescripcion"],
        "ciudad": None if tipo_operacion == 4 else location_codes["ciudad"],
        "ciudadDescripcion": None if tipo_operacion == 4 else location_codes["ciudadDescripcion"],
        "pais": "PRY" if tipo_operacion != 4 else pais_codigo,
        "paisDescripcion": "Paraguay" if tipo_operacion != 4 else pais_nombre,
        "tipoContribuyente": 1 if customer.customer_type == "Company" else 2,
        "documentoTipo": documento_tipo,
        "documentoNumero": documento_numero,
        "telefono": address_data.get("phone") or customer.mobile_no or "",
        "celular": address_data.get("phone") or customer.mobile_no or "",
        "email": address_data.get("email_id") or customer.email_id or "",
        "codigo": customer.sifen_codigo_cliente or ""
    }

    return cliente


def _get_customer_address(sales_invoice):
    """Get customer address from invoice or customer master."""
    address_data = {
        "address_line1": "",
        "address_line2": "",
        "city": "",
        "county": "",  # Distrito
        "state": "",
        "country": "Paraguay",
        "phone": "",
        "email_id": "",
        "sifen_numero_casa": ""
    }

    # Try to get from invoice address
    if hasattr(sales_invoice, 'customer_address') and sales_invoice.customer_address:
        try:
            address_doc = frappe.get_doc("Address", sales_invoice.customer_address)
            address_data.update({
                "address_line1": address_doc.address_line1 or "",
                "address_line2": address_doc.address_line2 or "",
                "city": address_doc.city or "",
                "county": address_doc.county or "",  # Distrito
                "state": address_doc.state or "",
                "country": address_doc.country or "Paraguay",
                "phone": address_doc.phone or "",
                "email_id": address_doc.email_id or "",
                "sifen_numero_casa": getattr(address_doc, 'sifen_numero_casa', '') or ""
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


def _get_documento_data(customer, customer_name):
    """Get document type and number."""
    documento_tipo = 1  # Default: RUC
    documento_numero = customer.tax_id or customer_name if customer else customer_name
    
    if customer and customer.sifen_tipo_documento:
        tipo_doc_str = str(customer.sifen_tipo_documento).strip()
        if '|' in tipo_doc_str:
            tipo_doc_str = tipo_doc_str.split('|')[0].strip()
        try:
            documento_tipo = int(tipo_doc_str)
        except (ValueError, TypeError):
            documento_tipo = 1
    
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
