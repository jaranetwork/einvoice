"""
Payment validation for SIFEN e-invoicing.
Validates payment terms, POS payments, and credit conditions.
"""

import frappe
from frappe import _


def validate_payment_sifen_fields(doc, is_pos_invoice, customer_country):
    """
    Validate all SIFEN required fields for Payments.
    
    Args:
        doc: Sales Invoice document
        is_pos_invoice: Whether invoice is POS
        customer_country: Customer country
    
    Returns:
        list: List of error messages
    """
    errors = []
    
    # Skip validation for Credit Notes
    is_return = hasattr(doc, 'is_return') and doc.is_return
    if is_return:
        return errors
    
    if is_pos_invoice:
        pos_errors = _validate_pos_payments(doc)
        errors.extend(pos_errors)
    else:
        normal_errors = _validate_normal_payments(doc)
        errors.extend(normal_errors)
    
    # Validate credit days for credit operations
    credit_errors = _validate_credit_days(doc, customer_country)
    errors.extend(credit_errors)
    
    return errors


def _validate_pos_payments(doc):
    """Validate POS payments."""
    errors = []
    has_pos_payments = False
    has_payment_terms = False
    
    # Skip validation for new documents (payments not saved yet)
    if doc.is_new():
        return errors

    # Check Payments
    if hasattr(doc, 'payments') and doc.payments:
        for payment in doc.payments:
            if payment.amount and payment.amount > 0:
                has_pos_payments = True
                break

    # Check Payment Terms
    if hasattr(doc, 'payment_schedule') and doc.payment_schedule:
        for term in doc.payment_schedule:
            if term.due_date and term.payment_amount and term.payment_amount > 0:
                has_payment_terms = True
                break

    # Check Payment Terms Template
    if hasattr(doc, 'payment_terms_template') and doc.payment_terms_template:
        has_payment_terms = True

    if not has_pos_payments and not has_payment_terms:
        errors.append(_("POS Invoice has no payment methods configured.<br><br>"
                       "Please add at least one payment method in the Payments table with amount > 0."))

    return errors


def _validate_normal_payments(doc):
    """Validate normal invoice payments."""
    errors = []
    has_payment_terms = False
    has_advances = False
    has_payment_terms_template = False
    
    # Skip validation for new documents (payments not saved yet)
    if doc.is_new():
        return errors

    # Check Payment Terms Template
    if hasattr(doc, 'payment_terms_template') and doc.payment_terms_template:
        has_payment_terms_template = True

    # Check Payment Schedule
    if hasattr(doc, 'payment_schedule') and doc.payment_schedule:
        for term in doc.payment_schedule:
            if term.due_date and term.payment_amount and term.payment_amount > 0:
                has_payment_terms = True
                break

    # Check Advances
    if hasattr(doc, 'advances') and doc.advances:
        for advance in doc.advances:
            if advance.allocated_amount and advance.allocated_amount > 0:
                has_advances = True
                break

    if not has_payment_terms and not has_advances and not has_payment_terms_template:
        if hasattr(doc, 'grand_total') and doc.grand_total and doc.grand_total > 0:
            errors.append(_("Invoice has no Payment Terms or Advances configured.<br><br>"
                          "Please add at least one of the following:<br>"
                          "1. Payment Terms Template<br>"
                          "2. Payment Schedule entries<br>"
                          "3. Advances"))

    return errors


def _validate_credit_days(doc, customer_country):
    """Validate credit days for credit operations."""
    errors = []
    
    # Skip for non-Paraguay customers
    is_paraguay = customer_country and customer_country == "Paraguay"
    if not is_paraguay:
        return errors
    
    # Skip if no payment schedule
    if not hasattr(doc, 'payment_schedule') or not doc.payment_schedule:
        return errors
    
    # Check if it's a credit operation
    from ..utils.utils import get_condicion_operacion
    condicion_operacion = get_condicion_operacion(doc)
    
    if condicion_operacion != 2:  # Not credit
        return errors
    
    # Validate credit days
    has_valid_plazo = False
    
    for term in doc.payment_schedule:
        credit_days = term.credit_days if hasattr(term, 'credit_days') else None
        if credit_days and int(credit_days) > 0:
            has_valid_plazo = True
            break
    
    if not has_valid_plazo:
        errors.append(_("Credit operation has no payment terms with days configured"))
    
    return errors
