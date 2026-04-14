"""
Control Number Helper for SIFEN e-invoicing.
Generates unique 9-digit control numbers for electronic invoices.
"""

import frappe
from frappe import _
import random


def generar_numero_control(company=None):
    """
    Generate unique 9-digit control code for SIFEN.

    Range: 000000001 to 999999999
    Uniqueness is global across Sales Invoice and Purchase Invoice (autofactura).
    Uses unique index in DB for O(1) verification.

    Args:
        company: Company name for uniqueness filter (optional)

    Returns:
        str: 9-digit unique code (with leading zeros)

    Raises:
        frappe.ValidationError: If unable to generate unique code after 10 attempts
    """
    max_intentos = 10

    for _ in range(max_intentos):
        # Generate random number between 1 and 999999999
        numero = random.randint(1, 999999999)
        # Format to 9 digits with leading zeros
        codigo = str(numero).zfill(9)

        # Check uniqueness across BOTH Sales Invoice and Purchase Invoice
        filters = {
            "custom_numero_control": codigo,
            "docstatus": ("!=", 2)  # Exclude cancelled
        }

        if company:
            filters["company"] = company

        existe_en_sales = frappe.db.exists("Sales Invoice", filters)
        existe_en_purchase = frappe.db.exists("Purchase Invoice", filters)

        if not existe_en_sales and not existe_en_purchase:
            return codigo

    # If we get here, too many collisions (very unlikely)
    frappe.throw(_(
        "Unable to generate unique control number after {0} attempts. "
        "Please try again in a few seconds."
    ).format(max_intentos))


def asignar_numero_control(doc, method=None):
    """
    Assign unique control number to invoice.

    Executed on Sales Invoice and Purchase Invoice validate events.
    Only generates new code if invoice doesn't have one.
    Uniqueness is global across both DocTypes (company + numero_control).

    Args:
        doc: Sales Invoice or Purchase Invoice document
        method: Event method name (unused)
    """
    # Only assign if no control number
    if not doc.custom_numero_control:
        doc.custom_numero_control = generar_numero_control(doc.company)
