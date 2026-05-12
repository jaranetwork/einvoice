"""
Control Number Helper for SIFEN e-invoicing.
Generates unique 9-digit control numbers using a centralized registry table.
Uniqueness is enforced by a DB-level unique index, eliminating SELECT queries.
"""

import frappe
from frappe import _
import random


def generar_numero_control(company=None, reference_doctype=None, reference_docname=None):
    """
    Generate unique 9-digit control code for SIFEN using centralized registry.

    Inserts into `tabSIFEN Control Number` with a UNIQUE index on
    (company, control_number) for O(1) atomic uniqueness enforcement.

    Args:
        company: Company name for uniqueness scope
        reference_doctype: Source doctype (Sales/Purchase Invoice, Delivery Note)
        reference_docname: Source document name

    Returns:
        str: 9-digit unique code (with leading zeros)

    Raises:
        frappe.ValidationError: If unable to generate unique code after 10 attempts
    """
    max_intentos = 10

    for _ in range(max_intentos):
        codigo = str(random.randint(1, 999999999)).zfill(9)

        try:
            doc = frappe.new_doc("SIFEN Control Number")
            doc.control_number = codigo
            doc.company = company or ""
            doc.assigned_on = frappe.utils.now_datetime()
            if reference_doctype:
                doc.reference_doctype = reference_doctype
                doc.reference_docname = reference_docname
            doc.insert()
            return codigo
        except frappe.DuplicateEntryError:
            continue

    frappe.throw(_(
        "Unable to generate unique control number after {0} attempts. "
        "Please try again in a few seconds."
    ).format(max_intentos))


def asignar_numero_control(doc, method=None):
    """
    Assign unique control number to invoice.

    Executed via doc_events on validate for Sales Invoice,
    Purchase Invoice, and Delivery Note.

    Args:
        doc: Sales Invoice, Purchase Invoice, or Delivery Note
        method: Event method name (unused)
    """
    if not doc.custom_numero_control:
        doc.custom_numero_control = generar_numero_control(
            company=doc.company,
            reference_doctype=doc.doctype,
            reference_docname=doc.name
        )
