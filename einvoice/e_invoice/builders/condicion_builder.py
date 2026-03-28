"""
Builds the CONDICION section of SIFEN payload.
Contains payment conditions, credit info, and delivery schedule.
"""

import frappe
from frappe.utils import flt


def build_condicion_section(sales_invoice, moneda="PYG", condicion_tipo_cambio=1):
    """
    Build the 'condicion' section with payment conditions.
    
    Args:
        sales_invoice: Sales Invoice document
        moneda: Currency code
        condicion_tipo_cambio: Exchange rate condition
    
    Returns:
        dict: Condicion section for SIFEN payload
    """
    # Get operation type (Contado vs Crédito)
    from ..utils.utils import get_condicion_operacion
    condicion_operacion = get_condicion_operacion(sales_invoice)
    
    # Build entregas (payment schedule)
    entregas = _build_entregas(sales_invoice, moneda, condicion_tipo_cambio)
    
    # Build condicion object
    condicion = {
        "tipo": condicion_operacion,
        "entregas": entregas
    }
    
    # Add credit info if credit operation
    if condicion_operacion == 2:
        credito_info = _build_credito_info(sales_invoice)
        if credito_info:
            condicion["credito"] = credito_info
    
    return condicion


def _build_entregas(sales_invoice, moneda, condicion_tipo_cambio):
    """Build entregas array from payment schedule."""
    entregas = []

    # Check if invoice has advances
    if hasattr(sales_invoice, 'advances') and sales_invoice.advances:
        for advance in sales_invoice.advances:
            if advance.allocated_amount and advance.allocated_amount > 0:
                entrega = {
                    "tipo": 5,  # Advance payment
                    "monto": str(abs(float(advance.allocated_amount))),
                    "moneda": moneda,
                    "cambio": condicion_tipo_cambio if moneda != "PYG" else 0
                }
                entregas.append(entrega)

    # Check payment schedule
    if hasattr(sales_invoice, 'payment_schedule') and sales_invoice.payment_schedule:
        for term in sales_invoice.payment_schedule:
            if term.payment_amount and term.payment_amount > 0:
                # Skip if already added as advance
                if _is_advance_already_added(term, entregas):
                    continue

                entrega = {
                    "tipo": _get_entrega_tipo(sales_invoice),
                    "monto": str(abs(float(term.payment_amount))),
                    "moneda": moneda,
                    "cambio": condicion_tipo_cambio if moneda != "PYG" else 0
                }
                entregas.append(entrega)

    # If no payment schedule, use grand total as single payment
    if not entregas and hasattr(sales_invoice, 'grand_total'):
        entrega = {
            "tipo": 1,  # Cash
            "monto": str(abs(float(sales_invoice.grand_total))),
            "moneda": moneda,
            "cambio": condicion_tipo_cambio if moneda != "PYG" else 0
        }
        entregas.append(entrega)

    return entregas


def _is_advance_already_added(term, entregas):
    """Check if advance was already added."""
    for entrega in entregas:
        if abs(float(entrega["monto"]) - float(term.payment_amount)) < 0.01:
            return True
    return False


def _get_entrega_tipo(sales_invoice):
    """Determine entrega tipo based on invoice type."""
    if hasattr(sales_invoice, 'is_pos') and sales_invoice.is_pos:
        return 1  # Cash
    return 2  # Credit


def _build_credito_info(sales_invoice):
    """Build credit information from payment terms."""
    credito_info = {
        "tipo": 1,  # Default: Plazo
        "plazo": "",
        "dDCondCred": "Plazo"
    }
    
    # Try to get days from payment terms
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
    Legacy function for backward compatibility.
    Use build_condicion_section instead.
    """
    return _build_entregas(sales_invoice, moneda, condicion_tipo_cambio)
