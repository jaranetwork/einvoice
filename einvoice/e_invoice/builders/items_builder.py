"""
Builds the ITEMS section of SIFEN payload.
Contains array of invoice items.
"""

import frappe
from ..helpers import (
    get_sifen_tipo_iva_item,
    get_sifen_unidad_medida,
)
from ..utils.utils import clean_html


def build_items_data(sales_invoice, moneda="PYG"):
    """
    Build the 'items' array with invoice items information.
    
    Args:
        sales_invoice: Sales Invoice document
        moneda: Currency code
    
    Returns:
        list: Items array for SIFEN payload
    """
    items = []
    
    for item in sales_invoice.items:
        item_data = _build_item_data(item, sales_invoice, moneda)
        items.append(item_data)
    
    return items


def _build_item_data(item, sales_invoice, moneda):
    """Build data for a single item."""
    # Get item details
    item_details = frappe.db.get_value(
        "Item",
        item.item_code,
        ["item_code", "stock_uom", "country_of_origin"],
        as_dict=True
    )
    
    # Get tax template
    item_tax_template = _get_item_tax_template(item, item_details)
    
    # Get SIFEN IVA data from Item Tax Template
    iva_tipo, iva_tasa = get_sifen_tipo_iva_item(item.item_code, item_tax_template, sales_invoice)
    
    # Determine IVA proportion
    iva_proporcion = _get_iva_proporcion(iva_tipo)
    
    # Get actual IVA rate
    iva = _get_iva_rate(iva_tipo, iva_tasa)
    
    # Get unit price
    precio_unitario = item.rate
    
    # Get unit of measure
    unidad_medida = get_sifen_unidad_medida(item_details.stock_uom if item_details else None)
    
    # Get exchange rate for item
    cambio_item = _get_cambio_item(moneda, sales_invoice)
    
    # Get discount
    descuento_item = _get_descuento_item(item, moneda)
    
    # Get country of origin
    pais_item, pais_descripcion = _get_pais_item(item_details)
    
    item = {
        "codigo": item.item_code,
        "descripcion": item.item_name,
        "observacion": "",
        "unidadMedida": unidad_medida,
        "cantidad": abs(item.qty) if _is_credit_debit_note(sales_invoice) else item.qty,
        "precioUnitario": precio_unitario,
       # "anticipo": 0,    ERPNext doesn't track advances at item level
        "pais": pais_item,
        "paisDescripcion": pais_descripcion,
        "ivaTipo": iva_tipo,
        "ivaProporcion": iva_proporcion,
        "iva": iva
    }

    # Add cambio section if applicable
    if cambio_item is not None:
        item["cambio"] = cambio_item
    
    # Add descuento section if applicable
    if descuento_item > 0:
        item["descuento"] = descuento_item

    return item

def _get_item_tax_template(item, item_details):
    """Get item tax template from item row, item_details, or Item Tax child table."""
    if hasattr(item, 'item_tax_template') and item.item_tax_template:
        return item.item_tax_template

    if item_details and item_details.get("item_tax_template"):
        return item_details.item_tax_template

    try:
        item_taxes = frappe.db.get_all(
            "Item Tax",
            filters={"parent": item.item_code},
            fields=["item_tax_template"],
            limit=1
        )
        if item_taxes:
            return item_taxes[0].item_tax_template
    except Exception:
        pass

    return None


def _get_iva_proporcion(iva_tipo):
    """Determine IVA proportion based on IVA type."""
    if iva_tipo in (2, 3):  # Exonerado, Exento
        return 0
    return 100  # Gravado, Parcial


def _get_iva_rate(iva_tipo, iva_tasa):
    """Get actual IVA rate based on type."""
    if iva_tipo in [1, 4]:  # Gravado, Gravado parcial
        return iva_tasa
    return 0  # ISC, Exento, Ninguno


def _get_cambio_item(moneda, doc):
    """Get exchange rate for item from Currency Exchange or invoice conversion_rate."""
    if moneda == "PYG":
        return None

    # Method 1: Try Currency Exchange from ERPNext
    if moneda != "PYG":
        exchange_rate = frappe.db.get_value(
            "Currency Exchange",
            {"from_currency": moneda, "to_currency": "PYG"},
            "exchange_rate"
        )
        if exchange_rate:
            return float(exchange_rate)

    # Method 2: Fallback to invoice conversion_rate
    if hasattr(doc, 'conversion_rate') and doc.conversion_rate:
        if doc.conversion_rate > 1:
            return float(doc.conversion_rate)

    return None


def _get_descuento_item(item, moneda):
    """Get discount amount for item.
    
    Note: SIFEN requires discount to be always positive.
    """
    descuento_item = 0

    if hasattr(item, 'discount_amount') and item.discount_amount:
        descuento_item = float(item.discount_amount)
    elif hasattr(item, 'distributed_discount_amount') and item.distributed_discount_amount:
        descuento_item = float(item.distributed_discount_amount)

    # SIFEN requires discount to be always positive
    descuento_item = abs(descuento_item)

    # Round according to SIFEN rules
    if descuento_item > 0:
        if moneda == "PYG":
            descuento_item = round(descuento_item)
        else:
            descuento_item = round(descuento_item, 8)

    return descuento_item


def _get_pais_item(item_details):
    """Get country of origin for item."""
    pais_item = "PRY"
    pais_descripcion = "Paraguay"
    
    if item_details and item_details.country_of_origin:
        country_data = frappe.db.get_value(
            "Country",
            item_details.country_of_origin,
            ["code", "country_name"],
            as_dict=True
        )
        
        if country_data and country_data.code:
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
                pais_descripcion = country_data.country_name or "Desconocido"
                alpha3 = frappe.db.get_value("Country", item_details.country_of_origin, "code_alpha3")
                if alpha3:
                    pais_item = alpha3
                else:
                    pais_item = pais_descripcion[:3].upper()
    
    return pais_item, pais_descripcion


def _is_credit_debit_note(sales_invoice):
    """Check if invoice is credit or debit note."""
    if hasattr(sales_invoice, 'is_return') and sales_invoice.is_return:
        return True
    if hasattr(sales_invoice, 'is_debit_note') and sales_invoice.is_debit_note:
        return True
    return False
