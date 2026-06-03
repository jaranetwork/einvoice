import frappe
from frappe import _
from einvoice.e_invoice.utils import (
    send_invoice_to_external_api,
    get_invoice_status,
    download_xml,
    download_pdf
)
import json


def generate_einvoice_manually(doc, method=None):
    """
    Generate electronic invoice automatically on submit.
    Called by hook: Delivery Note.on_submit
    """
    invoice_name = doc.name
    delivery_note = doc

    # Check if E-Invoice integration is enabled
    try:
        settings = frappe.get_single("E-Invoice Setting")
        if not settings.enabled:
            return  # Skip silently if not enabled
    except Exception:
        return

    # Skip if already generated
    if delivery_note.custom_einvoice_generated:
        return  # Skip silently if already generated

    # Validate invoice is submitted
    if delivery_note.docstatus != 1:
        return  # Skip silently if not submitted

    # Validate required fields before sending to external API
    try:
        validate_invoice_for_einvoice(delivery_note)
    except Exception as e:
        frappe.log_error(f"E-Invoice Validation Error: {str(e)}", "E-Invoice Validation")
        return  # Skip silently on validation error

    try:
        # Send invoice to external API
        result = send_invoice_to_external_api(delivery_note)

        if result["success"]:
            # Show formatted message as HTML
            frappe.msgprint(
                result["message"],
                title="E-Invoice Generated",
                indicator="green"
            )
        else:
            frappe.log_error(
                f"E-Invoice Generation Error for Invoice {delivery_note.name}: {result['message']}",
                "E-Invoice Error"
            )

    except Exception as e:
        frappe.log_error(
            f"E-Invoice Generation Error for Invoice {delivery_note.name}: {str(e)}",
            "E-Invoice Error"
        )


@frappe.whitelist()
def generate_einvoice_manually_button(invoice_name, regenerate=False):
    """Generate electronic invoice manually for a specific invoice (called from button)
    Only accessible by Administrator role.
    """
    # Verify user is Administrator
    from frappe.utils import get_fullname
    current_user = frappe.session.user

    # Check if current user has Administrator role
    user_roles = frappe.get_roles(current_user)
    if 'Administrator' not in user_roles:
        frappe.throw(
            _("Access Denied: Only Administrator can regenerate E-Invoices.<br><br>"
              "Current User: {0}<br><br>"
              "Please contact your system administrator.").format(get_fullname(current_user)),
            title=_("Permission Denied")
        )

    if not frappe.has_permission("Delivery Note", "write", invoice_name):
        frappe.throw(_("You do not have permission to modify this invoice"))

    delivery_note = frappe.get_doc("Delivery Note", invoice_name)

    # Check if E-Invoice integration is enabled
    try:
        settings = frappe.get_single("E-Invoice Setting")
        if not settings.enabled:
            frappe.throw(_("E-Invoice integration is not enabled"))
    except Exception:
        frappe.throw(_("E-Invoice settings not configured properly"))

    # Skip if already generated (unless regenerate flag is set)
    if delivery_note.custom_einvoice_generated and not regenerate:
        frappe.msgprint(
            _("E-Invoice already generated for this invoice.<br><br>"
              "If you need to regenerate, please use the 'Regenerate' button in the E-Invoice menu."),
            title=_("E-Invoice Already Generated"),
            indicator="orange"
        )
        return

    # Validate invoice is submitted
    if delivery_note.docstatus != 1:
        frappe.throw(_("Cannot generate E-Invoice for a draft invoice. Please submit the invoice first."))

    # Validate that a Delivery Trip exists
    has_trip = frappe.db.exists("Delivery Stop", {"delivery_note": delivery_note.name})
    if not has_trip:
        frappe.throw(
            _("Cannot generate E-Invoice without a Delivery Trip.<br><br>"
              "Please create a <b>Delivery Trip</b> (Viaje de Entrega) "
              "with a Delivery Stop linked to this Delivery Note first."),
            title=_("Delivery Trip Required")
        )

    # Validate required fields before sending to external API
    validate_invoice_for_einvoice(delivery_note)

    try:
        # Send invoice to external API
        result = send_invoice_to_external_api(delivery_note)

        if result["success"]:
            message = result["message"]
            if regenerate:
                message = _("E-Invoice regenerated and sent to SIFEN successfully!<br><br>") + message

            # Enqueue background job to check status periodically
            factura_id = result.get("data", {}).get("facturaId")
            if factura_id:
                frappe.enqueue(
                    "einvoice.e_invoice.utils.api_client.check_invoice_status_background",
                    invoice_name=invoice_name,
                    factura_id=factura_id,
                    user=frappe.session.user,
                    doctype="Delivery Note",
                )

            frappe.msgprint(
                message,
                title="E-Invoice Generated" if not regenerate else "E-Invoice Regenerated",
                indicator="green"
            )
            return result
        else:
            frappe.throw(_(f"Error generating E-Invoice: {result['message']}"))

    except Exception as e:
        error_msg = str(e)[:200]
        frappe.log_error(
            f"E-Invoice Generation Error for Invoice {delivery_note.name}: {error_msg}",
            "E-Invoice Error"
        )
        frappe.throw(_(f"Error generating E-Invoice: {error_msg}"))


def validate_invoice_for_einvoice(delivery_note):
    """
    Validate that all required fields are present before sending to SIFEN API.
    For Delivery Note, we validate company and customer data.
    """
    errors = []

    # Validate Company Tax ID
    company = frappe.get_doc("Company", delivery_note.company)
    if not company.tax_id:
        errors.append(_("Company Tax ID (RUC) is missing in Company {0}").format(delivery_note.company))

    # Validate Customer
    if not delivery_note.customer:
        errors.append(_("Customer is required"))

    # Get customer data for validation
    customer = None
    customer_country = ""
    customer_group = ""
    customer_type = ""
    customer_contribuyente = False
    customer_codigo = ""

    if delivery_note.customer:
        customer = frappe.db.get_value(
            "Customer",
            delivery_note.customer,
            ["customer_type", "customer_group", "tax_id", "sifen_contribuyente", "sifen_codigo_cliente"],
            as_dict=True
        )
        if customer:
            customer_type = customer.customer_type or ""
            customer_group = customer.customer_group or ""
            customer_contribuyente = bool(customer.sifen_contribuyente) if customer.sifen_contribuyente else False
            customer_codigo = customer.sifen_codigo_cliente or ""

        # Get country from customer's address
        if delivery_note.customer_address:
            address = frappe.db.get_value(
                "Address",
                delivery_note.customer_address,
                "country",
                as_dict=True
            )
            customer_country = address.country if address else ""

    # VALIDATION: Foreign customers (B2F) must be "No Contribuyente"
    if customer_country and customer_country != "Paraguay":
        if customer_contribuyente:
            errors.append(
                _("Foreign customers (country ≠ Paraguay) must be 'No Contribuyente'.<br><br>"
                  "Customer: {0}<br>"
                  "Country: {1}<br>"
                  "Current: Es contribuyente = Yes<br><br>"
                  "Please uncheck 'Es contribuyente?' in customer tax section.").format(
                    delivery_note.customer,
                    customer_country
                )
            )

    # VALIDATION: Customer must have sifen_codigo_cliente
    if not customer_codigo:
        errors.append(
            _("Customer {0} does not have SIFEN Code (sifen_codigo_cliente).<br><br>"
              "The code is required by SIFEN to identify the customer uniquely.<br><br>"
              "To fix this:<br>"
              "&nbsp;&nbsp;&nbsp;&nbsp;1. Go to Customer {0}<br>"
              "&nbsp;&nbsp;&nbsp;&nbsp;2. The code should be auto-generated (format: CUST-YYYY-#####)<br>"
              "&nbsp;&nbsp;&nbsp;&nbsp;3. If not generated, run the following command:<br>"
              "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;bench --site [site-name] execute einvoice.e_invoice.doctype.customer.update_existing_customers").format(
                delivery_note.customer
            )
        )

    # Determine tipoOperacion for validation
    tipo_operacion = None

    if customer:
        if customer_type == "Company":
            customer_group_lower = customer_group.lower() if customer_group else ""
            if "gubernamental" in customer_group_lower or "government" in customer_group_lower:
                tipo_operacion = 3  # B2G
            else:
                tipo_operacion = 1  # B2B
        elif customer_type == "Individual":
            if customer_country and customer_country != "Paraguay":
                tipo_operacion = 4  # B2F
            else:
                tipo_operacion = 2  # B2C

        # Override for customers without RUC
        if not customer.tax_id if customer else False:
            if customer_country and customer_country != "Paraguay":
                tipo_operacion = 4  # B2F
            else:
                tipo_operacion = 2  # B2C

    if tipo_operacion is None:
        errors.append(
            _("Could not determine tipoOperacion (tipo de operación) for customer {0}.<br><br>"
              "Customer Data:<br>"
              "- customer_type: {1}<br>"
              "- customer_group: {2}<br>"
              "- country: {3}<br>"
              "- tax_id: {4}<br><br>"
              "Please verify customer data is complete.").format(
                delivery_note.customer,
                customer_type or "N/A",
                customer_group or "N/A",
                customer_country or "N/A",
                customer.tax_id if customer else "N/A"
            )
        )
    else:
        # Validate according to tipoOperacion
        if tipo_operacion == 4:  # B2F - Foreigner
            # Validate country is NOT Paraguay
            if customer_country == "Paraguay":
                errors.append(
                    _("B2F (Foreigner) operation requires country different to Paraguay.<br><br>"
                      "Current country: {0}<br><br>"
                      "Please update customer address to have a country different to Paraguay.").format(
                        customer_country or "N/A"
                    )
                )

            # Validate customer is not contribuyente
            if delivery_note.customer:
                sifen_contribuyente = frappe.db.get_value(
                    "Customer",
                    delivery_note.customer,
                    "sifen_contribuyente"
                )
                if sifen_contribuyente:
                    errors.append(
                        _("B2F (Foreigner) operation requires customer to be 'No Contribuyente'.<br><br>"
                          "Current: Es contribuyente = Yes<br><br>"
                          "Please uncheck 'Es contribuyente?' in customer tax section.")
                    )

        else:  # B2B, B2C, B2G - Operations in Paraguay
            # Validate Customer Tax ID for B2B and B2G
            if tipo_operacion in [1, 3] and not (customer.tax_id if customer else False):
                errors.append(
                    _("Customer Tax ID (RUC) is required for {0} operation.<br><br>"
                      "Customer: {1}<br>"
                      "tipoOperacion: {2} ({3})<br><br>"
                      "Please set Tax ID in customer record.").format(
                        "B2B" if tipo_operacion == 1 else "B2G",
                        delivery_note.customer,
                        tipo_operacion,
                        "B2B" if tipo_operacion == 1 else "B2G"
                    )
                )

            # Validate address for B2B, B2C, B2G (Paraguay addresses only)
            if delivery_note.customer_address:
                address = frappe.get_doc("Address", delivery_note.customer_address)

                # Only validate state/county/city if country is Paraguay
                if address.country == "Paraguay":
                    # Validate state (departamento)
                    if not address.state:
                        errors.append(
                            _("Departamento (State) is required in customer address for tipoOperacion {0} (Paraguay).<br><br>"
                              "Address: {1}<br><br>"
                              "Please select a valid Paraguayan department using 🔍 Buscar Departamento button.").format(
                                tipo_operacion,
                                delivery_note.customer_address
                            )
                        )
                    else:
                        state_value = address.state.strip()
                        if state_value and not state_value.split('|')[0].isdigit():
                            errors.append(
                                _("Departamento (State) must be in format '1|CAPITAL' or '1'.<br><br>"
                                  "Current value: {0}<br><br>"
                                  "Please use 🔍 Buscar Departamento button to select a valid department.").format(
                                    address.state
                                )
                            )

                    # Validate county (distrito)
                    if not address.county:
                        errors.append(
                            _("Distrito (County) is required in customer address for tipoOperacion {0} (Paraguay).<br><br>"
                              "Address: {1}<br><br>"
                              "Please select a valid Paraguayan district.").format(
                                tipo_operacion,
                                delivery_note.customer_address
                            )
                        )

                    # Validate city (ciudad)
                    if not address.city:
                        errors.append(
                            _("Ciudad (City) is required in customer address for tipoOperacion {0} (Paraguay).<br><br>"
                              "Address: {1}<br><br>"
                              "Please select a valid Paraguayan city.").format(
                                tipo_operacion,
                                delivery_note.customer_address
                            )
                        )
                else:
                    # Non-Paraguay address - validate country is set
                    if not address.country:
                        errors.append(
                            _("Country is required in customer address for foreign customers.<br><br>"
                              "Address: {1}<br><br>"
                              "Please select the customer's country.").format(
                                tipo_operacion,
                                delivery_note.customer_address
                            )
                        )

    # Validate Company has establishment code
    if not hasattr(company, 'codigo_establecimiento') or not company.codigo_establecimiento:
        errors.append(_("Establishment Code (codigo_establecimiento) is missing in Company {0}").format(delivery_note.company))

    # Validate Company has timbrado
    if not hasattr(company, 'numero_timbrado') or not company.numero_timbrado:
        errors.append(_("Timbrado Number is missing in Company {0}").format(delivery_note.company))

    # Validate Company has tax regimen
    if not hasattr(company, 'tipo_regimen') or not company.tipo_regimen:
        errors.append(_("Tax Regimen (tipo_regimen) is missing in Company {0}").format(delivery_note.company))

    # Validate Company has economic activities
    if not hasattr(company, 'actividades_economicas') or not company.actividades_economicas:
        errors.append(_("Economic Activities are missing in Company {0}. Please add at least one activity.").format(delivery_note.company))
    elif len(company.actividades_economicas) == 0:
        errors.append(_("At least one Economic Activity is required in Company {0}.").format(delivery_note.company))
    else:
        for idx, actividad in enumerate(company.actividades_economicas):
            if not actividad.codigo_actividad:
                errors.append(_("Economic Activity #{0} is missing code.").format(idx + 1))
            if not actividad.descripcion_actividad:
                errors.append(_("Economic Activity #{0} is missing description.").format(idx + 1))

    # Validate SIFEN Responsible Person
    if not hasattr(company, 'sifen_responsable_tipo_documento') or not company.sifen_responsable_tipo_documento:
        errors.append(_("Responsible Person Document Type is missing in Company {0}").format(delivery_note.company))

    if not hasattr(company, 'sifen_respons_numero_documento') or not company.sifen_respons_numero_documento:
        errors.append(_("Responsible Person Document Number is missing in Company {0}").format(delivery_note.company))

    if not hasattr(company, 'sifen_responsable_nombre') or not company.sifen_responsable_nombre:
        errors.append(_("Responsible Person Name is missing in Company {0}").format(delivery_note.company))

    if not hasattr(company, 'sifen_responsable_cargo') or not company.sifen_responsable_cargo:
        errors.append(_("Responsible Person Position is missing in Company {0}").format(delivery_note.company))

    # Validate Items
    if not delivery_note.items:
        errors.append(_("No items found in invoice"))
    else:
        for idx, item in enumerate(delivery_note.items):
            if not item.item_code:
                errors.append(_("Item Code is required for item #{0}").format(idx + 1))
            if not item.rate:
                errors.append(_("Rate is required for item #{0} ({1})").format(idx + 1, item.item_code or "Unknown"))
            if not item.qty:
                errors.append(_("Quantity is required for item #{0} ({1})").format(idx + 1, item.item_code or "Unknown"))

    # Raise all errors at once
    if errors:
        frappe.throw(
            "<br><br>".join(errors),
            title=_("Missing Required Fields for E-Invoice")
        )


@frappe.whitelist()
def trigger_einvoice_generation(invoice_name):
    """Manually trigger E-Invoice generation for a specific invoice"""
    if not frappe.has_permission("Delivery Note", "write", invoice_name):
        frappe.throw(_("You do not have permission to modify this invoice"))

    return generate_einvoice_manually_button(invoice_name)


@frappe.whitelist()
def test_einvoice_connection():
    """Test connection to external E-Invoice API"""
    from einvoice.e_invoice.utils.api_client import test_api_connection

    result = test_api_connection()

    if result["success"]:
        frappe.msgprint(_(result["message"]), alert=True)
    else:
        frappe.msgprint(_(result["message"]), alert=True)

    return result


@frappe.whitelist()
def get_einvoice_status(invoice_name):
    """Get E-Invoice status for a specific invoice from local database"""
    if not frappe.has_permission("Delivery Note", "read", invoice_name):
        frappe.throw(_("You do not have permission to read this invoice"))

    invoice = frappe.get_doc("Delivery Note", invoice_name)

    # Validation 1: Check if invoice is submitted (not in draft)
    if invoice.docstatus == 0:
        frappe.throw(
            _("La factura está en estado <b>Borrador</b>.<br><br>"
              "Debe <b>Validar</b> la factura antes de verificar su estado en SIFEN.<br><br>"
              "<strong>Factura:</strong> {0}").format(invoice_name),
            title=_("Factura en Borrador")
        )

    # Validation 2: Check if E-Invoice was generated
    if not invoice.custom_einvoice_generated:
        frappe.throw(
            _("La factura <b>{0}</b> no tiene E-Invoice generado.<br><br>"
              "Debe enviar la factura a SIFEN primero usando:<br>"
              "<strong>E-Invoice → Send to SIFEN</strong><br><br>"
              "Estado actual: <b>{1}</b>").format(
                invoice_name,
                "Borrador" if invoice.docstatus == 0 else "Validada" if invoice.docstatus == 1 else "Cancelada"
            ),
            title=_("E-Invoice No Generado")
        )

    # Validation 3: Check if factura_id exists
    if not invoice.custom_sifen_factura_id:
        frappe.throw(
            _("La factura <b>{0}</b> no tiene Factura ID de SIFEN.<br><br>"
              "Esto puede deberse a:<br>"
              "1. El E-Invoice no se generó todavía<br>"
              "2. Hubo un error al generar el E-Invoice<br><br>"
              "Solución: Genere el E-Invoice primero.").format(invoice_name),
            title=_("Factura ID No Encontrado")
        )

    return {
        "generated": invoice.custom_einvoice_generated,
        "date": invoice.custom_einvoice_generated_date,
        "factura_id": invoice.custom_sifen_factura_id,
        "correlativo": invoice.custom_sifen_correlativo,
        "estado": invoice.custom_sifen_estado,
        "cdc": invoice.custom_sifen_cdc,
        "xml_link": invoice.custom_sifen_xml_link,
        "kude_link": invoice.custom_sifen_kude_link
    }


@frappe.whitelist()
def force_refresh_einvoice_status(invoice_name):
    """
    Force refresh E-Invoice status from SIFEN API.
    """
    if not frappe.has_permission("Delivery Note", "read", invoice_name):
        frappe.throw(_("You do not have permission to read this invoice"))

    invoice = frappe.get_doc("Delivery Note", invoice_name)

    factura_id = invoice.custom_sifen_factura_id

    if not factura_id:
        frappe.throw(
            _("No SIFEN Factura ID found. You need to generate the E-Invoice first."),
            title=_("Factura ID No Encontrado")
        )

    result = get_invoice_status(factura_id)

    if result["success"]:
        data = result.get("data", {})

        update_dict = {
            "custom_sifen_estado": data.get("estado") or invoice.custom_sifen_estado,
            "custom_sifen_correlativo": data.get("correlativo") or invoice.custom_sifen_correlativo,
        }
        cdc = data.get("cdc")
        if cdc:
            update_dict["custom_sifen_cdc"] = cdc

        frappe.db.set_value("Delivery Note", invoice_name, update_dict)
        frappe.db.commit()

        frappe.msgprint(
            _("Status updated successfully from SIFEN API<br/><br/>Factura ID: {0}<br/>Estado: {1}").format(
                factura_id, data.get("estado", "Unknown")
            ),
            alert=True
        )
    else:
        frappe.msgprint(
            _("SIFEN API returned: {0}<br/><br/>If the invoice was deleted in SIFEN, use '⚠️ Regenerate and Send' button.").format(
                result.get("message", "Unknown error")
            ),
            title=_("Warning"),
            indicator="orange"
        )

    return result


@frappe.whitelist()
def refresh_einvoice_status(invoice_name):
    """
    Refresh E-Invoice status from SIFEN API.
    """
    if not frappe.has_permission("Delivery Note", "read", invoice_name):
        frappe.throw(_("You do not have permission to read this invoice"))

    invoice = frappe.get_doc("Delivery Note", invoice_name)

    if not invoice.custom_sifen_factura_id:
        frappe.throw(_("No SIFEN Factura ID found for this invoice"))

    result = get_invoice_status(invoice.custom_sifen_factura_id)

    if result["success"]:
        data = result.get("data", {})

        update_dict = {
            "custom_sifen_estado": data.get("estado", invoice.custom_sifen_estado),
            "custom_sifen_cdc": data.get("cdc", invoice.custom_sifen_cdc),
            "custom_sifen_correlativo": data.get("correlativo", invoice.custom_sifen_correlativo),
        }

        frappe.db.set_value("Delivery Note", invoice_name, update_dict)
        frappe.db.commit()

        frappe.msgprint(
            _("Status updated successfully from SIFEN API<br/><br/>Factura ID: {0}<br/>Estado: {1}").format(
                invoice.custom_sifen_factura_id, data.get("estado", "Unknown")
            ),
            alert=True
        )
    else:
        frappe.msgprint(_(result["message"]), alert=True)

    return result


@frappe.whitelist()
def download_einvoice_xml(invoice_name):
    """
    Download XML document from SIFEN API.
    """
    if not frappe.has_permission("Delivery Note", "read", invoice_name):
        frappe.throw(_("You do not have permission to read this invoice"))

    invoice = frappe.get_doc("Delivery Note", invoice_name)

    if not invoice.custom_sifen_factura_id:
        frappe.throw(_("No SIFEN Factura ID found for this invoice"))

    result = download_xml(invoice.custom_sifen_factura_id)

    if result["success"]:
        frappe.msgprint(_("XML downloaded: {0}").format(result["file_url"]), alert=True)
    else:
        frappe.msgprint(_(result["message"]), alert=True)

    return result


@frappe.whitelist()
def download_einvoice_pdf(invoice_name):
    """
    Download PDF (KUDE) document from SIFEN API.
    """
    if not frappe.has_permission("Delivery Note", "read", invoice_name):
        frappe.throw(_("You do not have permission to read this invoice"))

    invoice = frappe.get_doc("Delivery Note", invoice_name)

    if not invoice.custom_sifen_factura_id:
        frappe.throw(_("No SIFEN Factura ID found for this invoice"))

    result = download_pdf(invoice.custom_sifen_factura_id)

    if result["success"]:
        frappe.msgprint(_("PDF downloaded: {0}").format(result["file_url"]), alert=True)
    else:
        frappe.msgprint(_(result["message"]), alert=True)

    return result


@frappe.whitelist()
def get_einvoice_preview_html(invoice_name):
    """
    Generate HTML preview for invoice without sending to SIFEN.
    Uses the same prepare_invoice_data() function that builds the JSON payload.
    """
    if not frappe.has_permission("Delivery Note", "read", invoice_name):
        frappe.throw(_("You do not have permission to read this invoice"))

    from einvoice.e_invoice.utils.preview import get_invoice_preview_html
    html = get_invoice_preview_html(invoice_name)
    return html


def on_cancel(doc, method=None):
    """
    Prevent cancellation if invoice is already accepted by SIFEN.
    """
    if doc.custom_sifen_estado and doc.custom_sifen_estado.lower() in ["aceptado", "accepted"]:
        frappe.throw(
            _("Cannot cancel this invoice because it is already <b>Accepted</b> by SIFEN.<br><br>"
              "Estado actual: {0}<br>"
              "CDC: {1}<br><br>"
              "Please create a Credit Note to correct this document.").format(
                doc.custom_sifen_estado,
                doc.custom_sifen_cdc or "N/A"
            ),
            title=_("Invoice Accepted by SIFEN")
        )
