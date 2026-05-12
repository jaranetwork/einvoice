import frappe


def configure_7_digit_naming_series():
    """Set 7-digit naming series for SIFEN documents via Property Setters.

    Runs on after_install and after_migrate to ensure the configuration
    persists across Docker restarts and bench migrate.
    """
    doctype_config = {
        "Sales Invoice": {
            "options": "ACC-SINV-.YYYY.-.#######\nACC-SINV-RET-.YYYY.-.#######",
            "default": "ACC-SINV-.YYYY.-.#######"
        },
        "Purchase Invoice": {
            "options": "ACC-PINV-.YYYY.-.#######\nACC-PINV-RET-.YYYY.-.#######",
            "default": "ACC-PINV-.YYYY.-.#######"
        },
        "Delivery Note": {
            "options": "MAT-DN-.YYYY.-.#######\nMAT-DN-RET-.YYYY.-.#######",
            "default": "MAT-DN-.YYYY.-.#######"
        }
    }

    for doctype, config in doctype_config.items():
        _set_options(doctype, config["options"])
        _set_default(doctype, config["default"])

    frappe.db.commit()


def _set_options(doctype, options):
    existing = frappe.db.get_value(
        "Property Setter",
        {"doc_type": doctype, "field_name": "naming_series", "property": "options"}
    )
    if existing:
        ps = frappe.get_doc("Property Setter", existing)
        if ps.value != options:
            ps.value = options
            ps.save()
    else:
        ps = frappe.get_doc({
            "doctype": "Property Setter",
            "doc_type": doctype,
            "doctype_or_field": "DocField",
            "field_name": "naming_series",
            "property": "options",
            "value": options,
            "property_type": "Text",
        })
        ps.insert()


def _set_default(doctype, default):
    existing = frappe.db.get_value(
        "Property Setter",
        {"doc_type": doctype, "field_name": "naming_series", "property": "default"}
    )
    if existing:
        ps = frappe.get_doc("Property Setter", existing)
        if ps.value != default:
            ps.value = default
            ps.save()
    else:
        ps = frappe.get_doc({
            "doctype": "Property Setter",
            "doc_type": doctype,
            "doctype_or_field": "DocField",
            "field_name": "naming_series",
            "property": "default",
            "value": default,
            "property_type": "Data",
        })
        ps.insert()
