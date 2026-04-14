"""
Currency Helper for SIFEN e-invoicing.
Validates currencies and calculates discounts.
"""

import frappe
from frappe import _

# SIFEN allowed currencies (ISO 4217)
VALID_CURRENCIES = [
    "PYG",  # Guaraní Paraguayo
    "USD",  # Dólar Estadounidense
    "EUR",  # Euro
    "ARS",  # Peso Argentino
    "BRL",  # Real Brasileño
    "CLP",  # Peso Chileno
    "UYU",  # Peso Uruguayo
    "MXN",  # Peso Mexicano
    "COP",  # Peso Colombiano
    "PEN",  # Sol Peruano
    "BOB",  # Boliviano
    "VEF",  # Bolívar Venezolano
    "GBP",  # Libra Esterlina
    "CHF",  # Franco Suizo
    "CAD",  # Dólar Canadiense
    "JPY",  # Yen Japonés
    "CNY",  # Yuan Chino
]


def validar_moneda_sifen(moneda, invoice_name):
    """
    Validate currency against SIFEN allowed currencies.
    
    Args:
        moneda: Currency code (ISO 4217)
        invoice_name: Invoice name for error message
    
    Raises:
        frappe.ValidationError: If currency is not allowed
    """
    if moneda not in VALID_CURRENCIES:
        frappe.throw(
            _("Currency '{0}' is not allowed for SIFEN e-invoicing.<br><br>"
              "<strong>Allowed currencies:</strong> {1}<br><br>"
              "<strong>Invoice:</strong> {2}").format(
                moneda,
                ', '.join(VALID_CURRENCIES),
                invoice_name
            ),
            title=_("Invalid Currency - SIFEN"),
            exc=frappe.ValidationError
        )


def get_descuento_global(sales_invoice, moneda="PYG"):
    """
    Calculate global discount from Sales Invoice.
    Uses "Additional Discount" / "Descuento adicional" from invoice level,
    NOT item-level discounts.

    Args:
        sales_invoice: Sales Invoice document
        moneda: Currency code for rounding rules

    Returns:
        float: Total discount rounded according to SIFEN rules
    """
    total_discount = 0

    # Get discount from invoice level (Additional Discount / Descuento adicional)
    if hasattr(sales_invoice, 'discount_amount') and sales_invoice.discount_amount:
        total_discount = float(sales_invoice.discount_amount)
    elif hasattr(sales_invoice, 'additional_discount_percentage') and sales_invoice.additional_discount_percentage:
        # Calculate from percentage if discount_amount is not set
        base_amount = sales_invoice.net_total or sales_invoice.total or 0
        if base_amount > 0:
            total_discount = base_amount * (float(sales_invoice.additional_discount_percentage) / 100)

    # Round according to SIFEN rules
    if total_discount > 0:
        if moneda == "PYG":
            # PYG: no decimals (integer)
            return round(total_discount)
        else:
            # Foreign currency: max 8 decimals
            return round(total_discount, 8)

    return 0
