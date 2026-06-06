"""
Mapping Helper for SIFEN e-invoicing.
Maps ERPNext codes to SIFEN codes.
"""

import frappe
from frappe import _


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
    
    # Weight/Mass
    if 'kg' in uom_lower or 'kilo' in uom_lower or 'kilogramo' in uom_lower:
        return 83  # kg - Kilogramos
    elif 'gr' in uom_lower or 'gramo' in uom_lower:
        return 86  # g - Gramos
    elif 'mg' in uom_lower or 'miligramo' in uom_lower:
        return 90  # MG - Miligramos
    elif 'tn' in uom_lower or 'tonelada' in uom_lower:
        return 99  # TN - Tonelada
    
    # Volume/Liquids
    elif 'lt' in uom_lower or 'litro' in uom_lower:
        return 89  # LT - Litros
    elif 'ml' in uom_lower or 'mililitro' in uom_lower:
        return 88  # ML - Mililitros
    elif 'm3' in uom_lower or 'metro cubico' in uom_lower:
        return 110  # M3 - Metros cúbicos
    
    # Length
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
    
    # Surface
    elif 'm2' in uom_lower or 'metro cuadrado' in uom_lower:
        return 109  # M2 - Metros cuadrados
    elif 'cm2' in uom_lower or 'cm cuadrado' in uom_lower:
        return 92  # CM2 - Centímetros cuadrados
    elif 'mm2' in uom_lower or 'mm cuadrado' in uom_lower:
        return 96  # MM2 - Milímetros cuadrados
    elif 'ha' in uom_lower or 'hectarea' in uom_lower:
        return 869  # ha - Hectáreas
    
    # Time
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
    
    # Others
    elif 'unidad' in uom_lower or 'nos' in uom_lower or 'pieza' in uom_lower:
        return 77  # UNI - Unidad
    elif 'global' in uom_lower or 'lote' in uom_lower:
        return 885  # GL - Unidad Medida Global
    elif 'ral' in uom_lower:  # Ración
        return 569  # ración - Ración
    
    # Default: Unidad
    return 77


def get_sifen_tipo_iva_item(item_code, item_tax_template=None, sales_invoice=None):
    """
    Get SIFEN IVA afectation code and tax rate from Item Tax Template Detail.
    
    Returns ivaTipo code (1-4) for items.
    
    SIFEN D013 - codigosAfectaciones (ivaTipo):
    1 = Gravado IVA (item con IVA)
    2 = Exonerado (Art.83- Ley 125/91)
    3 = Exento (no IVA)
    4 = Gravado parcial (Grav- Exento)
    
    Args:
        item_code: Item code string
        item_tax_template: Item Tax Template name (optional)
        sales_invoice: Sales Invoice object (optional, fallback)
    
    Returns:
        tuple: (afectacion_code, tax_rate)
            - afectacion_code: int (default: 1 - Gravado IVA)
            - tax_rate: float (default: 10.0)
    """
    if not item_code:
        return 1, 10.0
    
    # Get item's tax template from parameter or fetch from Item's Item Tax child table
    if not item_tax_template:
        try:
            item_taxes = frappe.db.get_all(
                "Item Tax",
                filters={"parent": item_code},
                fields=["item_tax_template"],
                limit=1
            )
            if item_taxes:
                item_tax_template = item_taxes[0].item_tax_template
        except Exception:
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
                        # Extract numeric value if stored as "1|Gravado"
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
    return 1, 10.0  # Default: Gravado IVA


def get_sifen_tipo_impuesto(doc):
    """
    Get SIFEN tax type from customer (SI) or supplier (PI) sifen_tipo_impuesto field.
    
    SIFEN D013 - tiposImpuestos (nivel factura):
    1 = IVA (cliente local contribuyente)
    2 = ISC (productos con impuesto selectivo)
    3 = Renta (cliente extranjero B2F con RUC)
    4 = Ninguno (cliente extranjero sin RUC, consumidor final)
    5 = IVA - Renta (mixto)
    
    Args:
        doc: Sales Invoice or Purchase Invoice document
    
    Returns:
        tuple: (tipo_impuesto, tax_rate)
            - tipo_impuesto: int (1-5) or None
            - tax_rate: float or None
    """
    party = None
    party_name = None
    party_doctype = None

    if hasattr(doc, 'customer') and doc.customer:
        party = frappe.db.get_value(
            "Customer", doc.customer,
            ["sifen_tipo_impuesto", "tax_id"], as_dict=True
        )
        party_name = doc.customer
        party_doctype = "Customer"
    elif hasattr(doc, 'supplier') and doc.supplier:
        party = frappe.db.get_value(
            "Supplier", doc.supplier,
            ["sifen_tipo_impuesto", "tax_id"], as_dict=True
        )
        party_name = doc.supplier
        party_doctype = "Supplier"

    if party and party.sifen_tipo_impuesto:
        tipo_impuesto_str = str(party.sifen_tipo_impuesto).strip()
        if '|' in tipo_impuesto_str:
            tipo_impuesto_str = tipo_impuesto_str.split('|')[0].strip()

        try:
            tipo_impuesto = int(tipo_impuesto_str)

            if tipo_impuesto < 1 or tipo_impuesto > 5:
                frappe.throw(
                    _("Invalid SIFEN Tipo Impuesto value for {0} {1}: {2}.<br><br>"
                      "Valid values are 1-5.").format(
                        party_doctype, party_name, tipo_impuesto
                    ),
                    title=_("Invalid SIFEN Tipo Impuesto")
                )

            if tipo_impuesto == 4:
                return tipo_impuesto, 0.0
            else:
                return tipo_impuesto, 10.0

        except (ValueError, TypeError):
            frappe.throw(
                _("Invalid SIFEN Tipo Impuesto format for {0} {1}: {2}.<br><br>"
                  "Please select a valid option (1-5).").format(
                    party_doctype, party_name, party.sifen_tipo_impuesto
                ),
                title=_("Invalid SIFEN Tipo Impuesto Format")
            )

    return None, None


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
