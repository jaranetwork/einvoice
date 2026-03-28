"""
Additional utility functions for SIFEN e-invoicing.
Contains helper functions that don't fit in other categories.
"""

import frappe
import requests
import base64
from frappe import _
from frappe.utils import now_datetime

# Constants
SIFEN_API_TIMEOUT = 30


def get_tipo_transaccion(sales_invoice):
    """
    Determine SIFEN transaction type based on invoice items.
    
    Types:
    1 = Sale of merchandise
    2 = Service provision
    3 = Mixed (merchandise and services)
    4 = Sale of fixed assets
    5 = Sale of foreign currency
    6 = Purchase of foreign currency
    7 = Promotion or sample delivery
    8 = Donation
    9 = Advance payment
    10 = Purchase of products
    11 = Purchase of services
    12 = Sale of credit fiscal
    13 = Medical samples
    
    Args:
        sales_invoice: Sales Invoice document
    
    Returns:
        int: Transaction type (1-13)
    """
    has_products = False
    has_services = False
    has_fixed_asset = False
    
    for item in sales_invoice.items:
        # Get item type from Item doctype
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
    
    # Priority: Fixed Asset > Mixed > Services > Merchandise
    if has_fixed_asset:
        return 4  # Sale of fixed assets
    elif has_products and has_services:
        return 3  # Mixed
    elif has_services:
        return 2  # Service provision
    else:
        return 1  # Sale of merchandise


def get_indicador_presencia(sales_invoice):
    """
    Determine SIFEN presencia indicator based on invoice type.
    
    Indicators:
    1 = Presencial (con entrega física del bien)
    2 = Presencial (sin entrega física del bien)
    3 = No presencial
    
    Args:
        sales_invoice: Sales Invoice document
    
    Returns:
        int: Presencia indicator (1-3)
    """
    # If POS invoice, it's presencial with physical delivery
    if hasattr(sales_invoice, 'is_pos') and sales_invoice.is_pos:
        return 1
    
    # If service items, it's presencial without physical delivery
    for item in sales_invoice.items:
        item_data = frappe.db.get_value("Item", item.item_code, "is_stock_item", as_dict=True)
        if item_data and not item_data.is_stock_item:
            return 2
    
    # Default: presencial with physical delivery
    return 1


def get_condicion_anticipo(sales_invoice):
    """
    Determine SIFEN anticipo condition based on ERPNext advance payments.
    
    Conditions:
    1 = Global advance (single advance for entire document)
    2 = Item-level advance (advance distribution by item)
    
    Args:
        sales_invoice: Sales Invoice document
    
    Returns:
        int: Anticipo condition (1-2)
    """
    # Check if there are advances allocated
    if hasattr(sales_invoice, 'advances') and sales_invoice.advances:
        # Multiple advances = Item-level
        if len(sales_invoice.advances) > 1:
            return 2
        else:
            return 1
    
    # No advances
    return 1


def get_condicion_operacion(sales_invoice):
    """
    Determine SIFEN payment condition (Contado vs Crédito).
    
    Conditions:
    1 = Contado (immediate payment)
    2 = Crédito (deferred payment)
    
    Args:
        sales_invoice: Sales Invoice document
    
    Returns:
        int: Payment condition (1-2)
    """
    # Check outstanding amount
    if hasattr(sales_invoice, 'outstanding_amount') and sales_invoice.outstanding_amount:
        if sales_invoice.outstanding_amount > 0:
            return 2  # Crédito
    
    # Check payment terms
    if hasattr(sales_invoice, 'payment_terms_template') and sales_invoice.payment_terms_template:
        return 2  # Crédito
    
    # Check payment schedule
    if hasattr(sales_invoice, 'payment_schedule') and sales_invoice.payment_schedule:
        # Multiple payment schedules = Crédito
        if len(sales_invoice.payment_schedule) > 1:
            return 2
        
        # Single schedule with future due date = Crédito
        if sales_invoice.payment_schedule[0].due_date:
            from frappe.utils import date_diff
            days = date_diff(sales_invoice.payment_schedule[0].due_date, sales_invoice.posting_date)
            if days > 0:
                return 2
    
    # Default: Contado
    return 1


def get_credito_info(sales_invoice):
    """
    Get credit information from payment terms.
    
    Args:
        sales_invoice: Sales Invoice document
    
    Returns:
        dict: Credit information
    """
    credito_info = {
        "tipo": 1,  # Plazo
        "plazo": "",
        "dDCondCred": "Plazo"
    }
    
    # Try to get days from payment schedule
    if hasattr(sales_invoice, 'payment_schedule') and sales_invoice.payment_schedule:
        total_days = 0
        for term in sales_invoice.payment_schedule:
            if hasattr(term, 'credit_days') and term.credit_days:
                total_days += int(term.credit_days)
        
        if total_days > 0:
            credito_info["plazo"] = str(total_days)
            return credito_info
    
    # Try to get from payment terms template
    if hasattr(sales_invoice, 'payment_terms_template') and sales_invoice.payment_terms_template:
        try:
            template = frappe.get_doc("Payment Terms Template", sales_invoice.payment_terms_template)
            if template.terms:
                total_days = sum([int(term.credit_days or 0) for term in template.terms])
                if total_days > 0:
                    credito_info["plazo"] = str(total_days)
                    return credito_info
        except Exception:
            pass
    
    # Fallback: calculate days from posting date to due date
    if hasattr(sales_invoice, 'payment_schedule') and sales_invoice.payment_schedule:
        for term in sales_invoice.payment_schedule:
            if term.due_date and term.payment_amount and term.payment_amount > 0:
                try:
                    from frappe.utils import date_diff
                    days = date_diff(term.due_date, sales_invoice.posting_date)
                    if days > 0:
                        credito_info["plazo"] = str(days)
                        return credito_info
                except Exception:
                    pass
    
    return credito_info


def get_condicion_entregas(sales_invoice, moneda, condicion_tipo_cambio):
    """
    Build entregas array from payment schedule.
    
    Args:
        sales_invoice: Sales Invoice document
        moneda: Currency code
        condicion_tipo_cambio: Exchange rate condition
    
    Returns:
        list: Entregas array
    """
    entregas = []
    
    # Check if invoice has advances
    if hasattr(sales_invoice, 'advances') and sales_invoice.advances:
        for idx, advance in enumerate(sales_invoice.advances):
            if advance.allocated_amount and advance.allocated_amount > 0:
                entrega = {
                    "numero": idx + 1,
                    "monto": abs(float(advance.allocated_amount)),
                    "fecha": str(advance.reference_date) if advance.reference_date else None,
                    "tipo": 5,  # Advance payment
                    "cambio": condicion_tipo_cambio if moneda != "PYG" else 1
                }
                entregas.append(entrega)
    
    # Check payment schedule
    if hasattr(sales_invoice, 'payment_schedule') and sales_invoice.payment_schedule:
        for idx, term in enumerate(sales_invoice.payment_schedule):
            if term.payment_amount and term.payment_amount > 0:
                # Skip if already added as advance
                if _is_advance_already_added(term, entregas):
                    continue
                
                entrega = {
                    "numero": len(entregas) + 1,
                    "monto": abs(float(term.payment_amount)),
                    "fecha": str(term.due_date) if term.due_date else None,
                    "tipo": 1 if hasattr(sales_invoice, 'is_pos') and sales_invoice.is_pos else 2,
                    "cambio": condicion_tipo_cambio if moneda != "PYG" else 1
                }
                entregas.append(entrega)
    
    # If no payment schedule, use grand total as single payment
    if not entregas and hasattr(sales_invoice, 'grand_total'):
        entrega = {
            "numero": 1,
            "monto": abs(float(sales_invoice.grand_total)),
            "fecha": str(sales_invoice.posting_date) if hasattr(sales_invoice, 'posting_date') else None,
            "tipo": 1,  # Cash
            "cambio": condicion_tipo_cambio if moneda != "PYG" else 1
        }
        entregas.append(entrega)
    
    return entregas


def _is_advance_already_added(term, entregas):
    """Check if advance was already added."""
    for entrega in entregas:
        if abs(entrega["monto"] - float(term.payment_amount)) < 0.01:
            return True
    return False


def get_actividades_economicas(company):
    """
    Get economic activities for a company.
    
    Args:
        company: Company name or document
    
    Returns:
        list: List of dictionaries with 'codigo' and 'descripcion'
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
        dict: Dictionary with 'numero_timbrado' and 'fecha_timbrado'
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
        int: 1 = Persona Física, 2 = Persona Jurídica
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
        int: 1-8 (Turismo, Importador, Exportador, Maquila, Ley 60/90, Pequeño Productor, Mediano Productor, Contable)
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
        
        # Priority 1: Try to get preferred billing address
        if address_names:
            try:
                address_doc = frappe.get_doc("Address", address_names[0])
                if address_doc.address_type == "Billing" and address_doc.is_primary_address == 1:
                    address = {
                        "address_line1": address_doc.address_line1 or "",
                        "address_line2": address_doc.address_line2 or "",
                        "city": address_doc.city or "",
                        "state": address_doc.state or "",
                        "county": address_doc.county or "",
                        "sifen_numero_casa": getattr(address_doc, 'sifen_numero_casa', '') or "",
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
                            "sifen_numero_casa": getattr(address_doc, 'sifen_numero_casa', '') or "",
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
                            "sifen_numero_casa": getattr(address_doc, 'sifen_numero_casa', '') or "",
                            "country": address_doc.country or "",
                            "phone": address_doc.phone or "",
                            "email_id": address_doc.email_id or ""
                        }
                        break
            except Exception:
                pass
        
        # Fallback: Get any address
        if not address and address_names:
            try:
                address_doc = frappe.get_doc("Address", address_names[0])
                address = {
                    "address_line1": address_doc.address_line1 or "",
                    "address_line2": address_doc.address_line2 or "",
                    "city": address_doc.city or "",
                    "state": address_doc.state or "",
                    "county": address_doc.county or "",
                    "sifen_numero_casa": getattr(address_doc, 'sifen_numero_casa', '') or "",
                    "country": address_doc.country or "",
                    "phone": address_doc.phone or "",
                    "email_id": address_doc.email_id or ""
                }
            except Exception:
                pass
        
        if address:
            address_data.update(address)

            # Parse location codes
            location_codes = get_paraguay_location_codes(
                address.get("state", ""),
                address.get("county", ""),  # Distrito
                address.get("city", ""),
                address.get("country", "")
            )
            address_data.update(location_codes)
    except Exception:
        pass

    return address_data


def get_usuario_from_invoice(sales_invoice):
    """
    Get user information from invoice owner or SIFEN responsible person from Company.
    Priority: SIFEN Responsible Person > Invoice Owner
    
    Returns dictionary with user data for data.usuario field.
    """
    usuario = {
        "documentoTipo": 1,
        "documentoNumero": "",
        "nombre": "Vendedor",
        "cargo": "Vendedor"
    }
    
    # First, try to get SIFEN responsible person from Company
    try:
        company = frappe.get_doc("Company", sales_invoice.company)
        
        if hasattr(company, 'sifen_responsable_tipo_documento') and company.sifen_responsable_tipo_documento:
            tipo_doc = str(company.sifen_responsable_tipo_documento).strip()
            if '|' in tipo_doc:
                tipo_doc = tipo_doc.split('|')[0].strip()
            usuario["documentoTipo"] = int(tipo_doc)
        
        if hasattr(company, 'sifen_respons_numero_documento') and company.sifen_respons_numero_documento:
            usuario["documentoNumero"] = company.sifen_respons_numero_documento
        
        if hasattr(company, 'sifen_responsable_nombre') and company.sifen_responsable_nombre:
            usuario["nombre"] = company.sifen_responsable_nombre
        
        if hasattr(company, 'sifen_responsable_cargo') and company.sifen_responsable_cargo:
            usuario["cargo"] = company.sifen_responsable_cargo
        
        # Return early if we found SIFEN responsible person data
        if usuario["documentoNumero"] or usuario["nombre"] != "Vendedor":
            return usuario
    except Exception:
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


def clean_html(text):
    """
    Remove HTML tags from text.
    
    Args:
        text: String that may contain HTML tags
    
    Returns:
        str: Clean text without HTML tags
    """
    import re
    
    if not text:
        return ""
    
    # Remove HTML tags using regex
    clean = re.sub(r'<[^>]+>', '', text)
    
    # Remove extra whitespace and newlines
    clean = ' '.join(clean.split())
    
    return clean.strip()


def get_paraguay_location_codes(state, county, city, country):
    """
    Get Paraguay location codes from address data.

    Args:
        state: State/department string
        county: County/distrito string
        city: City string
        country: Country string

    Returns:
        dict: Location codes and descriptions
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

    # Process district (county)
    if county:
        county_code = ""
        county_clean = county
        if "|" in county:
            parts = county.split("|", 1)
            county_code = parts[0]
            county_clean = parts[1]

        result["distritoDescripcion"] = county_clean

        if county_code:
            result["distrito"] = int(county_code)

    # Process city
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

    return result


def get_country_codes(customer_country):
    """
    Get country code and name for SIFEN.
    
    Args:
        customer_country: Customer country name
    
    Returns:
        tuple: (pais_codigo, pais_nombre)
    """
    if not customer_country:
        return "PRY", "Paraguay"
    
    # Direct mapping from country name to SIFEN code
    country_mapping = {
        "Paraguay": ("PRY", "Paraguay"),
        "Argentina": ("ARG", "Argentina"),
        "Brasil": ("BRA", "Brasil"),
        "Brazil": ("BRA", "Brasil"),
        "Chile": ("CHL", "Chile"),
        "Uruguay": ("URY", "Uruguay"),
        "Bolivia": ("BOL", "Bolivia"),
        "Estados Unidos": ("USA", "Estados Unidos"),
        "United States": ("USA", "Estados Unidos"),
        "España": ("ESP", "España"),
        "Alemania": ("DEU", "Alemania"),
        "México": ("MEX", "México"),
        "Colombia": ("COL", "Colombia"),
        "Perú": ("PER", "Perú"),
        "Ecuador": ("ECU", "Ecuador"),
        "Japón": ("JPN", "Japón"),
        "China": ("CHN", "China"),
    }
    
    # Try direct mapping first
    if customer_country in country_mapping:
        return country_mapping[customer_country]
    
    # Try to get from Frappe Country doctype
    country_code = frappe.db.get_value("Country", customer_country, "code")
    
    if country_code:
        # Convert alpha-2 to alpha-3
        alpha2_to_alpha3 = {
            "PY": "PRY", "AR": "ARG", "BR": "BRA", "US": "USA",
            "CL": "CHL", "UY": "URY", "BO": "BOL", "DE": "DEU",
            "ES": "ESP", "MX": "MEX", "CO": "COL", "PE": "PER",
            "EC": "ECU", "JP": "JPN", "KR": "KOR", "IT": "ITA",
            "FR": "FRA", "GB": "GBR", "CA": "CAN", "AU": "AUS",
            "IN": "IND", "RU": "RUS", "CN": "CHN"
        }
        
        pais_codigo = country_code.upper()
        if pais_codigo in alpha2_to_alpha3:
            return alpha2_to_alpha3[pais_codigo], customer_country
    
    # Default to Paraguay
    return "PRY", customer_country
