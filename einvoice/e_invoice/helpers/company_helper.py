"""
Company Helper for SIFEN e-invoicing.
Contains helper functions for company data.
"""

import frappe


def get_actividades_economicas(company):
    """
    Get economic activities for a company.

    Args:
        company: Company name or document

    Returns:
        list: List of dictionaries with 'codigo' and 'descripcion'
    """
    actividades = []

    try:
        company_doc = frappe.get_doc("Company", company) if isinstance(company, str) else company

        if hasattr(company_doc, 'actividades_economicas') and company_doc.actividades_economicas:
            for actividad in company_doc.actividades_economicas:
                actividades.append({
                    "codigo": actividad.codigo_actividad,
                    "descripcion": actividad.descripcion_actividad
                })
    except Exception:
        # Return empty list if lookup fails
        pass

    return actividades


def get_timbrado_info(company):
    """
    Get timbrado information from company.

    Args:
        company: Company name or document

    Returns:
        dict: Dictionary with 'numero_timbrado' and 'fecha_timbrado'
    """
    timbrado = {
        "numero_timbrado": "",
        "fecha_timbrado": ""
    }

    try:
        company_doc = frappe.get_doc("Company", company) if isinstance(company, str) else company

        if hasattr(company_doc, 'numero_timbrado'):
            timbrado["numero_timbrado"] = company_doc.numero_timbrado

        if hasattr(company_doc, 'fecha_timbrado') and company_doc.fecha_timbrado:
            # Convert date object to string for JSON serialization
            timbrado["fecha_timbrado"] = str(company_doc.fecha_timbrado)
    except Exception:
        # Return empty values if lookup fails
        pass

    return timbrado


def get_tipo_contribuyente(company):
    """
    Get contributor type from company.

    Args:
        company: Company name or document

    Returns:
        int: 1 = Persona Física, 2 = Persona Jurídica
    """
    tipo = 1  # Default: Persona Física

    try:
        company_doc = frappe.get_doc("Company", company) if isinstance(company, str) else company

        if hasattr(company_doc, 'tipo_contribuyente') and company_doc.tipo_contribuyente:
            # Convert to int if it's a string
            try:
                tipo = int(company_doc.tipo_contribuyente)
            except (ValueError, TypeError):
                tipo = 1
    except Exception:
        # Return default if lookup fails
        pass

    return tipo


def get_tipo_regimen(company):
    """
    Get tax regimen type from company.

    Args:
        company: Company name or document

    Returns:
        int: 1-8 (Turismo, Importador, Exportador, Maquila, Ley 60/90, Pequeño Productor, Mediano Productor, Contable)
    """
    tipo = 8  # Default: Régimen Contable

    try:
        company_doc = frappe.get_doc("Company", company) if isinstance(company, str) else company

        if hasattr(company_doc, 'tipo_regimen') and company_doc.tipo_regimen:
            # Convert to int if it's a string
            try:
                tipo = int(company_doc.tipo_regimen)
            except (ValueError, TypeError):
                tipo = 8
    except Exception:
        # Return default if lookup fails
        pass

    return tipo
