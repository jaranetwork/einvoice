#!/usr/bin/env python3
"""
Validación de Dirección para SIFEN Paraguay
Valida que Departamento, Distrito y Ciudad coincidan según los datos de SIFEN
"""

import frappe
from .sifen_data import DEPARTAMENTOS, DISTRITOS, CIUDADES


def parse_sifen_field(value):
    """
    Parsea el valor de un campo SIFEN que puede estar en formato:
    - Solo código: "145"
    - Código|Descripcion: "145|CIUDAD DEL ESTE"
    
    Retorna el código extraído
    """
    if not value:
        return None
    
    value = str(value).strip()
    if '|' in value:
        # Formato "codigo|descripcion"
        return value.split('|')[0].strip()
    return value


def validate_address_sifen(doc, method=None):
    """
    Valida que los campos SIFEN de Address sean consistentes:
    - La ciudad debe pertenecer al distrito seleccionado
    - El distrito debe pertenecer al departamento seleccionado

    Se ejecuta como hook antes de guardar (validate)
    Usa los campos estándar: state (Departamento), county (Distrito) y city (Ciudad)
    
    NOTA: 
    - La validación SOLO aplica si country = Paraguay
    - Para Paraguay: state, county y city son OBLIGATORIOS
    """
    # Solo validar si el país es Paraguay
    if doc.country and doc.country != "Paraguay":
        return
    
    # Solo validar si al menos uno de los campos SIFEN existe
    if not (doc.state or doc.county or doc.city):
        return

    errores = []

    # Extraer códigos de los campos estándar
    dept_codigo = parse_sifen_field(doc.state)
    distrito_codigo = parse_sifen_field(doc.county)
    ciudad_codigo = parse_sifen_field(doc.city)

    # Para Paraguay: state, county y city son OBLIGATORIOS
    if not dept_codigo:
        errores.append("El campo <b>Estado / Departamento / Provincia</b> es obligatorio para direcciones en Paraguay.")
    
    if not distrito_codigo:
        errores.append("El campo <b>Distrito</b> es obligatorio para direcciones en Paraguay. Usá el botón 🔍 Buscar Distrito para seleccionar.")
    
    if not ciudad_codigo:
        errores.append("El campo <b>Ciudad</b> es obligatorio para direcciones en Paraguay. Usá el botón 🔍 Buscar Ciudad para seleccionar.")

    # Si faltan campos obligatorios, no continuar con validaciones
    if errores:
        frappe.throw(
            "<h4>Errores de validación de dirección SIFEN:</h4><ul>" +
            "".join([f"<li>{e}</li>" for e in errores]) +
            "</ul>",
            title="Validación de Dirección Paraguay"
        )

    # Validar Ciudad -> Distrito
    ciudad_data = CIUDADES.get(str(ciudad_codigo))
    if ciudad_data:
        distrito_ciudad_id = str(ciudad_data.get('distrito'))
        if str(distrito_codigo) != distrito_ciudad_id:
            distrito_nombre = DISTRITOS.get(str(distrito_codigo), {}).get('descripcion', distrito_codigo)
            ciudad_nombre = ciudad_data.get('descripcion', ciudad_codigo)
            distrito_correcto = DISTRITOS.get(distrito_ciudad_id, {}).get('descripcion', distrito_ciudad_id)
            errores.append(
                f"El distrito <b>{distrito_nombre}</b> no pertenece a la ciudad "
                f"<b>{ciudad_nombre}</b>. Esta ciudad pertenece al distrito "
                f"<b>{distrito_correcto}</b> (código {distrito_ciudad_id})."
            )
    else:
        errores.append(f"El código de ciudad <b>{ciudad_codigo}</b> no es válido según SIFEN.")

    # Validar Distrito -> Departamento
    distrito_data = DISTRITOS.get(str(distrito_codigo))
    if distrito_data:
        departamento_distrito_id = str(distrito_data.get('departamento'))
        if str(dept_codigo) != departamento_distrito_id:
            departamento_nombre = DEPARTAMENTOS.get(str(dept_codigo), dept_codigo)
            distrito_nombre = distrito_data.get('descripcion', distrito_codigo)
            departamento_correcto = DEPARTAMENTOS.get(departamento_distrito_id, departamento_distrito_id)
            errores.append(
                f"El departamento <b>{departamento_nombre}</b> no pertenece al distrito "
                f"<b>{distrito_nombre}</b>. Este distrito pertenece al departamento "
                f"<b>{departamento_correcto}</b> (código {departamento_distrito_id})."
            )
    else:
        errores.append(f"El código de distrito <b>{distrito_codigo}</b> no es válido según SIFEN.")

    # Validar que el departamento sea válido
    if dept_codigo and str(dept_codigo) not in DEPARTAMENTOS:
        errores.append(f"El código de departamento <b>{dept_codigo}</b> no es válido según SIFEN.")

    # Lanzar excepción si hay errores
    if errores:
        frappe.throw(
            "<h4>Errores de validación de dirección SIFEN:</h4><ul>" +
            "".join([f"<li>{e}</li>" for e in errores]) +
            "</ul>",
            title="Validación de Dirección Paraguay"
        )


def get_departamentos():
    """Retorna la lista de departamentos para usar en Select"""
    return [{"label": f"{codigo} - {nombre}", "value": codigo} 
            for codigo, nombre in sorted(DEPARTAMENTOS.items())]


@frappe.whitelist()
def get_distritos_by_departamento(departamento_codigo):
    """Retorna los distritos de un departamento específico"""
    return [
        {"label": f"{codigo} - {data['descripcion']}", "value": codigo}
        for codigo, data in sorted(DISTRITOS.items())
        if str(data['departamento']) == str(departamento_codigo)
    ]


@frappe.whitelist()
def get_ciudades_by_distrito(distrito_codigo):
    """Retorna las ciudades de un distrito específico"""
    return [
        {"label": f"{codigo} - {data['descripcion']}", "value": codigo}
        for codigo, data in sorted(CIUDADES.items())
        if str(data['distrito']) == str(distrito_codigo)
    ]


def get_full_address_data(doc):
    """
    Retorna los datos completos de la dirección incluyendo códigos SIFEN
    Para usar en la generación de JSON para SIFEN
    Usa los campos estándar: state (Departamento), county (Distrito) y city (Ciudad)
    """
    dept_codigo = parse_sifen_field(doc.state)
    distrito_codigo = parse_sifen_field(doc.county)
    ciudad_codigo = parse_sifen_field(doc.city)

    return {
        'departamento_codigo': dept_codigo,
        'departamento_nombre': DEPARTAMENTOS.get(str(dept_codigo), ''),
        'distrito_codigo': distrito_codigo,
        'distrito_nombre': DISTRITOS.get(str(distrito_codigo), {}).get('descripcion', ''),
        'ciudad_codigo': ciudad_codigo,
        'ciudad_nombre': CIUDADES.get(str(ciudad_codigo), {}).get('descripcion', ''),
        'numero_casa': doc.sifen_numero_casa,
        'address_line1': doc.address_line1,
        'address_line2': doc.address_line2,
        'pincode': doc.pincode,
    }


@frappe.whitelist()
def get_sifen_data_for_autocomplete(type):
    """
    Retorna datos SIFEN para autocompletado
    type: 'distrito' o 'ciudad'
    """
    if type == 'distrito':
        return [f"{codigo}|{data['descripcion']}" for codigo, data in sorted(DISTRITOS.items())]
    elif type == 'ciudad':
        return [f"{codigo}|{data['descripcion']}" for codigo, data in sorted(CIUDADES.items())]
    return []


@frappe.whitelist()
def search_sifen(type, search_term, departamento_codigo=None):
    """
    Busca en los datos SIFEN
    type: 'distrito' o 'ciudad'
    search_term: término de búsqueda
    departamento_codigo: filtro opcional para distritos
    """
    results = []
    search_term = str(search_term).upper().strip()
    
    if type == 'distrito':
        for codigo, data in DISTRITOS.items():
            # Filtrar por departamento si se especifica
            if departamento_codigo and str(data['departamento']) != str(departamento_codigo):
                continue
            
            # Buscar en código y descripción
            if search_term in str(codigo) or search_term in data['descripcion'].upper():
                results.append({
                    'value': codigo,
                    'label': f"{codigo}|{data['descripcion']}"
                })
                
                # Limitar a 50 resultados
                if len(results) >= 50:
                    break
    
    elif type == 'ciudad':
        for codigo, data in CIUDADES.items():
            if search_term in str(codigo) or search_term in data['descripcion'].upper():
                results.append({
                    'value': codigo,
                    'label': f"{codigo}|{data['descripcion']}"
                })
                
                # Limitar a 50 resultados
                if len(results) >= 50:
                    break
    
    return results[:50]


@frappe.whitelist()
def search_ciudad_por_distrito(search_term, distrito_codigo=None):
    """
    Busca ciudades filtrando por distrito
    search_term: término de búsqueda
    distrito_codigo: filtro de distrito (requerido)
    """
    results = []
    search_term = str(search_term).upper().strip()
    
    for codigo, data in CIUDADES.items():
        # Filtrar por distrito si se especifica
        if distrito_codigo and str(data['distrito']) != str(distrito_codigo):
            continue
        
        # Buscar en código y descripción
        if search_term in str(codigo) or search_term in data['descripcion'].upper():
            results.append({
                'value': codigo,
                'label': f"{codigo}|{data['descripcion']}"
            })
            
            # Limitar a 50 resultados
            if len(results) >= 50:
                break
    
    return results[:50]
