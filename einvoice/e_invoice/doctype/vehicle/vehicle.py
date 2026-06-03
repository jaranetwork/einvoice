import frappe
from frappe import _


def validate(doc, method=None):
    _validar_chasis_no(doc)


def _validar_chasis_no(doc):
    if not doc.chassis_no:
        frappe.throw(_(
            "El campo N° de Chasis es obligatorio para vehículos SIFEN.<br><br>"
            "Este número se utiliza como:<br>"
            "- Número de identificación (VIN) cuando Tipo Identificación = Chasis<br>"
            "- Número de Matrícula cuando Tipo Identificación = Matrícula"
        ))
