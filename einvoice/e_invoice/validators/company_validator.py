"""
Company validation for SIFEN e-invoicing.
Validates all required company fields for electronic invoicing.
"""

import frappe
from frappe import _


def validate_company_sifen_fields(doc, company):
    """
    Validate all SIFEN required fields for Company.
    
    Args:
        doc: Sales Invoice document
        company: Company document
    
    Returns:
        list: List of error messages
    """
    errors = []
    
    # Validate Tax ID (RUC)
    if not company.tax_id:
        errors.append(_("Company Tax ID (RUC) is missing in Company {0}").format(doc.company))
    
    # Validate Establishment Code
    if not hasattr(company, 'codigo_establecimiento') or not company.codigo_establecimiento:
        errors.append(_("Establishment Code (codigo_establecimiento) is missing in Company {0}").format(doc.company))
    elif len(company.codigo_establecimiento) > 3:
        errors.append(_("Establishment Code cannot exceed 3 digits. Current value: {0}").format(
            company.codigo_establecimiento
        ))
    
    # Validate Timbrado Number
    if not hasattr(company, 'numero_timbrado') or not company.numero_timbrado:
        errors.append(_("Timbrado Number is missing in Company {0}").format(doc.company))
    
    # Validate Timbrado Date
    if not hasattr(company, 'fecha_timbrado') or not company.fecha_timbrado:
        errors.append(_("Timbrado Date is missing in Company {0}").format(doc.company))
    
    # Validate Contributor Type
    if not hasattr(company, 'tipo_contribuyente') or not company.tipo_contribuyente:
        errors.append(_("Contributor Type is missing in Company {0}").format(doc.company))
    
    # Validate Tax Regimen
    if not hasattr(company, 'tipo_regimen') or not company.tipo_regimen:
        errors.append(_("Tax Regimen Type is missing in Company {0}").format(doc.company))
    
    # Validate Economic Activities
    _validate_economic_activities(company, errors)
    
    # Validate SIFEN Responsible Person
    _validate_responsable_sifen(company, errors)
    
    return errors


def _validate_economic_activities(company, errors):
    """Validate economic activities child table."""
    if not hasattr(company, 'actividades_economicas') or not company.actividades_economicas:
        errors.append(_("Economic Activities are missing in Company {0}. Please add at least one activity.").format(
            company.name
        ))
    elif len(company.actividades_economicas) == 0:
        errors.append(_("At least one Economic Activity is required in Company {0}.").format(company.name))
    else:
        for idx, actividad in enumerate(company.actividades_economicas):
            if not actividad.codigo_actividad:
                errors.append(_("Economic Activity #{0} is missing code.").format(idx + 1))
            if not actividad.descripcion_actividad:
                errors.append(_("Economic Activity #{0} is missing description.").format(idx + 1))


def _validate_responsable_sifen(company, errors):
    """Validate SIFEN responsible person fields."""
    responsable_fields = [
        ('sifen_responsable_tipo_documento', "Responsible Person Document Type"),
        ('sifen_respons_numero_documento', "Responsible Person Document Number"),
        ('sifen_responsable_nombre', "Responsible Person Name"),
        ('sifen_responsable_cargo', "Responsible Person Position"),
    ]

    for fieldname, label in responsable_fields:
        if not hasattr(company, fieldname) or not getattr(company, fieldname):
            errors.append(_("{0} is missing in Company {1}").format(label, company.name))
