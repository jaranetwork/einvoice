"""
Customer validation for SIFEN e-invoicing.
Validates all required customer fields and address for electronic invoicing.
"""

import frappe
from frappe import _


def validate_customer_sifen_fields(doc, customer_data, customer_country, tipo_operacion):
    """
    Validate all SIFEN required fields for Customer.
    
    Args:
        doc: Sales Invoice document
        customer_data: Customer data dict
        customer_country: Customer country
        tipo_operacion: Operation type (1=B2B, 2=B2C, 3=B2G, 4=B2F)
    
    Returns:
        list: List of error messages
    """
    errors = []
    
    if not customer_data:
        return errors
    
    # Validate SIFEN Document Type (only required if customer is NOT a contributor)
    is_contribuyente = customer_data.get('sifen_contribuyente', False)
    customer_sifen_tipo_documento = customer_data.get('sifen_tipo_documento', '')

    if not is_contribuyente and not customer_sifen_tipo_documento:
        errors.append(_("SIFEN Document Type is empty for customer {0}").format(doc.customer))
    elif customer_sifen_tipo_documento:
        _validate_tipo_documento(errors, doc, customer_sifen_tipo_documento, tipo_operacion)
    
    # Validate SIFEN Tax Type
    customer_sifen_tipo_impuesto = customer_data.get('sifen_tipo_impuesto', '')
    if not customer_sifen_tipo_impuesto:
        errors.append(_("SIFEN Tax Type is empty for customer {0}").format(doc.customer))
    else:
        _validate_tipo_impuesto(errors, doc, customer_sifen_tipo_impuesto, tipo_operacion)
    
    # Validate RUC for B2B/B2G
    if tipo_operacion in [1, 3] and not customer_data.get('tax_id'):
        errors.append(_("Customer Tax ID (RUC) is required for {0} operation").format(
            "B2B" if tipo_operacion == 1 else "B2G"
        ))
    
    # Validate address for Paraguay customers
    if tipo_operacion in [1, 2, 3] and customer_country == "Paraguay":
        _validate_paraguay_address(doc, errors)
    
    return errors


def _validate_tipo_documento(errors, doc, tipo_documento, tipo_operacion):
    """Validate document type according to operation type."""
    tipo_documento_codigo = str(tipo_documento).split('|')[0].strip() if '|' in str(tipo_documento) else str(tipo_documento)
    
    if tipo_operacion in [1, 3] and tipo_documento_codigo != "1":
        errors.append(_("Customer for {0} operation must have SIFEN Document Type = 'RUC'").format(
            "B2B" if tipo_operacion == 1 else "B2G"
        ))
    elif tipo_operacion == 2 and tipo_documento_codigo not in ["1", "2"]:
        errors.append(_("Customer for B2C operation must have SIFEN Document Type = 'RUC' or 'CI'"))
    elif tipo_operacion == 4 and tipo_documento_codigo not in ["3", "4"]:
        errors.append(_("Foreign customer (B2F) must have SIFEN Document Type = 'Pasaporte' or 'Otro'"))


def _validate_tipo_impuesto(errors, doc, tipo_impuesto, tipo_operacion):
    """Validate tax type according to operation type."""
    tipo_impuesto_codigo = str(tipo_impuesto).split('|')[0].strip() if '|' in str(tipo_impuesto) else str(tipo_impuesto)
    
    if tipo_operacion in [1, 2, 3]:  # Paraguay operations
        if tipo_impuesto_codigo in ["3", "4"]:
            errors.append(_("SIFEN Tax Type is not coherent with operation type {0}").format(tipo_operacion))
    elif tipo_operacion == 4:  # Foreign operations
        if tipo_impuesto_codigo not in ["3", "4"]:
            errors.append(_("SIFEN Tax Type is not coherent with B2F operation"))


def _validate_paraguay_address(doc, errors):
    """Validate Paraguay address fields."""
    if doc.customer_address:
        address = frappe.get_doc("Address", doc.customer_address)
        
        if not address.state:
            errors.append(_("Department (State) is required in customer address for Paraguay operations"))
        
        if not address.county:
            errors.append(_("District (County) is required in customer address for Paraguay operations"))
        
        if not address.city:
            errors.append(_("City is required in customer address for Paraguay operations"))
