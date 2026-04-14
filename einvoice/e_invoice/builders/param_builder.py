"""
Builds the PARAM section of SIFEN payload.
Contains company/emitter information.
"""

import frappe
from ..helpers import get_actividades_economicas, get_timbrado_info


def build_param_section(company, establecimiento):
    """
    Build the 'param' section with company/emitter information.

    Args:
        company: Company document
        establecimiento: Establishment code

    Returns:
        dict: Param section for SIFEN payload
    """
    # Get economic activities
    actividades_economicas = get_actividades_economicas(company)

    # Get timbrado info
    timbrado = get_timbrado_info(company)

    # Get company address
    from ..utils.utils import get_company_address
    address_data = get_company_address(company.name)

    # Get email from company
    email = getattr(company, 'email', None) or getattr(company, 'email_id', '')
    
    # Parse tipo_contribuyente (format: "1|Persona Física" → 1)
    tipo_contribuyente_raw = getattr(company, 'tipo_contribuyente', '1')
    tipo_contribuyente_str = str(tipo_contribuyente_raw).split('|')[0].strip() if '|' in str(tipo_contribuyente_raw) else str(tipo_contribuyente_raw)
    try:
        tipo_contribuyente = int(tipo_contribuyente_str)
    except (ValueError, TypeError):
        tipo_contribuyente = 1
    
    # Parse tipo_regimen (format: "8|Régimen Contable" → 8)
    tipo_regimen_raw = getattr(company, 'tipo_regimen', '8')
    tipo_regimen_str = str(tipo_regimen_raw).split('|')[0].strip() if '|' in str(tipo_regimen_raw) else str(tipo_regimen_raw)
    try:
        tipo_regimen = int(tipo_regimen_str)
    except (ValueError, TypeError):
        tipo_regimen = 8

    param = {
        "version": 150,
        "ruc": company.tax_id,
        "razonSocial": company.name,
        "nombreFantasia": getattr(company, 'sifen_denominacion', '') or company.name,
        "actividadesEconomicas": actividades_economicas,
        "timbradoNumero": timbrado.get("numero_timbrado", ""),
        "timbradoFecha": timbrado.get("fecha_timbrado", ""),
        "tipoContribuyente": tipo_contribuyente,
        "tipoRegimen": tipo_regimen,
        "establecimientos": [{
            "codigo": establecimiento,
            "denominacion": getattr(company, 'sifen_denominacion', ''),
            "direccion": address_data.get("address_line1"),
            "numeroCasa": address_data.get("sifen_numero_casa"),
            "complementoDireccion1": address_data.get("address_line1"),
            "complementoDireccion2": address_data.get("address_line2"),
            "departamento": address_data.get("departamento"),
            "departamentoDescripcion": address_data.get("departamentoDescripcion"),
            "distrito": address_data.get("distrito"),
            "distritoDescripcion": address_data.get("distritoDescripcion"),
            "ciudad": address_data.get("ciudad"),
            "ciudadDescripcion": address_data.get("ciudadDescripcion"),
            "telefono": address_data.get("phone"),
            "email": address_data.get("email_id") or email
        }]
    }
    
    return param
