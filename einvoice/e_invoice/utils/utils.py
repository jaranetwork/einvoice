"""
Additional utility functions for SIFEN e-invoicing.
Contains helper functions that don't fit in other categories.
"""

import frappe
import requests
import base64
from frappe import _
from frappe.utils import now_datetime, flt

# Constants
SIFEN_API_TIMEOUT = 30


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
    Only returns a value if there are actual advances.

    Note: ERPNext advances are document-level, not item-level.
    Therefore we always return 1 (Global) when advances exist.

    Conditions:
    1 = Anticipo Global (single advance for entire document)

    Args:
        sales_invoice: Sales Invoice document

    Returns:
        int or None: 1 if advances exist, or None if no advances
    """
    # Check if there are advances allocated
    if hasattr(sales_invoice, 'advances') and sales_invoice.advances:
        total_advance = sum(abs(adv.allocated_amount or 0) for adv in sales_invoice.advances)
        if total_advance > 0:
            # ERPNext advances are always document-level, so always Global
            return 1

    # No advances - return None so field is not sent
    return None


def get_condicion_operacion(sales_invoice):
    """
    Determine SIFEN payment condition (Contado vs Crédito).
    
    Conditions:
    1 = Contado (immediate payment)
    2 = Crédito (deferred payment)
    
    Args:
        sales_invoice: Sales Invoice or Purchase Invoice document
    
    Returns:
        int: Payment condition (1-2)
    """
    # Check is_paid for Purchase Invoice
    if hasattr(sales_invoice, 'is_paid') and sales_invoice.is_paid:
        return 1  # Contado (already paid)
    
    # Check outstanding amount
    if hasattr(sales_invoice, 'outstanding_amount') and sales_invoice.outstanding_amount is not None:
        if flt(sales_invoice.outstanding_amount) <= 0:
            return 1  # Contado (fully paid)
        return 2  # Crédito (outstanding balance)
    
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
    Get credit information from payment terms for SIFEN.

    Args:
        sales_invoice: Sales Invoice or Purchase Invoice document

    Returns:
        dict: Credit information for SIFEN
            - tipo: 1 = Plazo (días), 2 = Cuotas (installments)
            - plazo: Días de crédito (required if tipo = 1)
            - cuotas: Cantidad de cuotas (required if tipo = 2)
            - montoEntrega: Monto de entrega inicial (optional, if first term due date = invoice date)
            - infoCuotas: Array con detalles de cada cuota (required if tipo = 2)
    """
    credito_info = {
        "tipo": 1,  # Default: Plazo (días)
        "plazo": "",
        "cuotas": 0,
        "infoCuotas": []
    }

    # Try to get from payment schedule
    if hasattr(sales_invoice, 'payment_schedule') and sales_invoice.payment_schedule:
        # Check if there's a single payment term with invoice_portion = 100%
        # This means it's a simple credit with days (tipo = 1)
        has_100_percent = False
        total_days = 0
        
        for term in sales_invoice.payment_schedule:
            # Check if invoice_portion is 100%
            if hasattr(term, 'invoice_portion') and term.invoice_portion:
                invoice_portion = float(term.invoice_portion)
                if invoice_portion == 100:
                    has_100_percent = True
                    # Get credit days from this term
                    if hasattr(term, 'credit_days') and term.credit_days:
                        total_days += int(term.credit_days)
            # Fallback: check credit_days even without invoice_portion
            elif hasattr(term, 'credit_days') and term.credit_days:
                total_days += int(term.credit_days)

        # If single payment term with 100% invoice portion → tipo 1 (Plazo en días)
        if has_100_percent and len(sales_invoice.payment_schedule) == 1:
            credito_info["tipo"] = 1  # Plazo (días)
            if total_days > 0:
                credito_info["plazo"] = str(total_days)
            return credito_info

        # Multiple payment terms or partial payments → tipo 2 (Cuotas)
        if len(sales_invoice.payment_schedule) > 1 or (has_100_percent is False and len(sales_invoice.payment_schedule) == 1):
            credito_info["tipo"] = 2  # Cuotas
            credito_info["cuotas"] = len(sales_invoice.payment_schedule)

            # Check if first payment term has same date as invoice (initial delivery)
            first_term = sales_invoice.payment_schedule[0]
            if first_term.due_date and first_term.payment_amount:
                from frappe.utils import getdate
                posting_date = getdate(sales_invoice.posting_date)
                due_date = getdate(first_term.due_date)
                if posting_date == due_date:
                    credito_info["montoEntrega"] = float(first_term.payment_amount)

            info_cuotas = []
            for term in sales_invoice.payment_schedule:
                info_cuota = {
                    "moneda": getattr(sales_invoice, 'currency', 'PYG'),
                    "monto": float(term.payment_amount) if term.payment_amount else 0,
                    "vencimiento": str(term.due_date) if term.due_date else None
                }
                info_cuotas.append(info_cuota)

            credito_info["infoCuotas"] = info_cuotas
            return credito_info

        # Single term but not 100% - use days if available
        if total_days > 0:
            credito_info["tipo"] = 1  # Plazo (días)
            credito_info["plazo"] = str(total_days)
            return credito_info

    # Try to get from payment terms template
    if hasattr(sales_invoice, 'payment_terms_template') and sales_invoice.payment_terms_template:
        try:
            template = frappe.get_doc("Payment Terms Template", sales_invoice.payment_terms_template)
            if template.terms:
                # Check if there's only one term with 100%
                if len(template.terms) == 1:
                    term = template.terms[0]
                    if hasattr(term, 'invoice_portion') and term.invoice_portion:
                        invoice_portion = float(term.invoice_portion)
                        if invoice_portion == 100:
                            credito_info["tipo"] = 1  # Plazo (días)
                            if hasattr(term, 'credit_days') and term.credit_days:
                                credito_info["plazo"] = str(int(term.credit_days))
                            return credito_info
                
                # Multiple terms → Cuotas
                credito_info["tipo"] = 2  # Cuotas
                credito_info["cuotas"] = len(template.terms)

                # Check if first term has credit_days = 0 (means same date as invoice)
                first_term = template.terms[0]
                if hasattr(first_term, 'credit_days') and first_term.credit_days == 0:
                    # Calculate amount based on invoice portion
                    first_term_amount = (float(first_term.invoice_portion or 0) / 100) * float(sales_invoice.grand_total or 0)
                    if first_term_amount > 0:
                        credito_info["montoEntrega"] = first_term_amount

                info_cuotas = []
                for term in template.terms:
                    info_cuota = {
                        "moneda": getattr(sales_invoice, 'currency', 'PYG'),
                        "monto": 0,  # Will be calculated later
                        "vencimiento": None
                    }
                    if hasattr(term, 'credit_days') and term.credit_days:
                        info_cuota["dias"] = int(term.credit_days)
                    info_cuotas.append(info_cuota)

                credito_info["infoCuotas"] = info_cuotas
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
                        credito_info["tipo"] = 1  # Plazo (días)
                        credito_info["plazo"] = str(days)
                        return credito_info
                except Exception:
                    pass

    return credito_info


def get_condicion_entregas(doc, moneda, condicion_tipo_cambio=None):
    """
    Build entregas array from payment schedule.
    Gets exchange rate from Currency Exchange first.

    Args:
        doc: Sales Invoice or Purchase Invoice document
        moneda: Currency code
        condicion_tipo_cambio: Exchange rate condition (deprecated, kept for compatibility)

    Returns:
        list: Entregas array
    """
    # Get exchange rate from Currency Exchange
    cambio_valor = 0
    if moneda != "PYG":
        cambio_valor = frappe.db.get_value(
            "Currency Exchange",
            {"from_currency": moneda, "to_currency": "PYG"},
            "exchange_rate"
        )
        if not cambio_valor and hasattr(doc, 'conversion_rate') and doc.conversion_rate:
            cambio_valor = doc.conversion_rate

    entregas = []

    # Check if invoice has advances
    if hasattr(doc, 'advances') and doc.advances:
        for idx, advance in enumerate(doc.advances):
            if advance.allocated_amount and advance.allocated_amount > 0:
                entrega = {
                    "numero": idx + 1,
                    "monto": abs(float(advance.allocated_amount)),
                    "fecha": str(advance.reference_date) if advance.reference_date else None,
                    "tipo": 5,  # Advance payment
                    "cambio": cambio_valor if moneda != "PYG" else 1
                }
                entregas.append(entrega)

    # Check payment schedule
    if hasattr(doc, 'payment_schedule') and doc.payment_schedule:
        for idx, term in enumerate(doc.payment_schedule):
            if term.payment_amount and term.payment_amount > 0:
                # Skip if already added as advance
                if _is_advance_already_added(term, entregas):
                    continue

                entrega = {
                    "numero": len(entregas) + 1,
                    "monto": abs(float(term.payment_amount)),
                    "fecha": str(term.due_date) if term.due_date else None,
                    "tipo": 1 if hasattr(doc, 'is_pos') and doc.is_pos else 2,
                    "cambio": cambio_valor if moneda != "PYG" else 1
                }
                entregas.append(entrega)

    # If no payment schedule, use grand total as single payment
    if not entregas and hasattr(doc, 'grand_total'):
        entrega = {
            "numero": 1,
            "monto": abs(float(doc.grand_total)),
            "fecha": str(doc.posting_date) if hasattr(doc, 'posting_date') else None,
            "tipo": 1,  # Cash
            "cambio": cambio_valor if moneda != "PYG" else 1
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
