"""
Items validation for SIFEN e-invoicing.
Validates all required item fields and tax templates.
"""

import frappe
from frappe import _


def validate_items_sifen_fields(doc, customer_country):
    """
    Validate all SIFEN required fields for Items.
    
    Args:
        doc: Sales Invoice document
        customer_country: Customer country
    
    Returns:
        list: List of error messages
    """
    errors = []
    
    if not doc.items:
        errors.append(_("No items found in invoice"))
        return errors
    
    for idx, item in enumerate(doc.items):
        item_errors = _validate_item(doc, item, idx, customer_country)
        errors.extend(item_errors)
    
    return errors


def _validate_item(doc, item, idx, customer_country):
    """Validate a single item."""
    errors = []
    item_num = idx + 1
    
    # Basic item fields
    if not item.item_code:
        errors.append(_("Item Code is required for item #{0}").format(item_num))
    if not item.rate:
        errors.append(_("Rate is required for item #{0} ({1})").format(item_num, item.item_code or "Unknown"))
    if not item.qty:
        errors.append(_("Quantity is required for item #{0} ({1})").format(item_num, item.item_code or "Unknown"))
    
    # Validate Item Tax Template
    tax_template_errors = _validate_item_tax_template(item, item_num, customer_country)
    errors.extend(tax_template_errors)
    
    return errors


def _validate_item_tax_template(item, item_num, customer_country):
    """Validate item tax template and SIFEN fields."""
    errors = []
    tax_template_name = None
    
    # Get tax template from item or item master
    if hasattr(item, 'item_tax_template') and item.item_tax_template:
        tax_template_name = item.item_tax_template
    else:
        # Try to get from Item master
        try:
            tax_template_name = frappe.db.get_value("Item", item.item_code, "item_tax_template")
        except Exception:
            pass
    
    if not tax_template_name:
        errors.append(_("Item #{0} ({1}) has no Item Tax Template configured").format(
            item_num, item.item_code or "Unknown"
        ))
        return errors
    
    # Validate tax template details
    try:
        taxes = frappe.db.get_all(
            "Item Tax Template Detail",
            filters={"parent": tax_template_name},
            fields=["sifen_tipo_iva", "tax_rate", "tax_type"],
            order_by="idx"
        )
        
        if not taxes or len(taxes) == 0:
            errors.append(_("Item Tax Template '{0}' has no tax lines configured").format(tax_template_name))
            return errors
        
        # Validate SIFEN Tipo IVA and tax rates
        has_sifen_tipo = False
        has_positive_rate = False
        
        for tax in taxes:
            if tax.sifen_tipo_iva:
                has_sifen_tipo = True
                sifen_errors = _validate_sifen_tipo_iva(tax, tax_template_name, item_num)
                errors.extend(sifen_errors)
            
            if tax.tax_rate and float(tax.tax_rate) > 0:
                has_positive_rate = True
        
        # Validate tax rate for Paraguay customers
        if customer_country == "Paraguay" and not has_positive_rate and not has_sifen_tipo:
            errors.append(_("Item Tax Template '{0}' has all taxes with 0% rate for taxable items").format(
                tax_template_name
            ))
        
        if not has_sifen_tipo:
            errors.append(_("Item Tax Template '{0}' has no 'SIFEN Tipo IVA' configured").format(tax_template_name))
    
    except Exception as e:
        errors.append(_("Error validating Item Tax Template '{0}': {1}").format(tax_template_name, str(e)))
    
    return errors


def _validate_sifen_tipo_iva(tax, tax_template_name, item_num):
    """Validate SIFEN Tipo IVA value."""
    errors = []
    
    try:
        sifen_value = str(tax.sifen_tipo_iva).strip()
        if '|' in sifen_value:
            sifen_value = sifen_value.split('|')[0].strip()
        
        sifen_code = int(sifen_value)
        
        if sifen_code < 1 or sifen_code > 4:
            errors.append(_("Item Tax Template '{0}' has invalid SIFEN Tipo IVA value: {1}. Valid values: 1-4").format(
                tax_template_name, tax.sifen_tipo_iva
            ))
    except (ValueError, TypeError):
        errors.append(_("Item Tax Template '{0}' has non-numeric SIFEN Tipo IVA value: {1}").format(
            tax_template_name, tax.sifen_tipo_iva
        ))
    
    return errors
