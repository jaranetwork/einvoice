import frappe
from frappe.model.document import Document

class EInvoiceSetting(Document):
    def validate(self):
        if self.enabled and not self.api_endpoint:
            frappe.throw("API Endpoint is required when E-Invoice is enabled")

        if self.enabled and not self.api_key:
            frappe.throw("API Key is required when E-Invoice is enabled")

        if self.enabled and not self.tipo_emision:
            frappe.throw("Tipo de Emisión is required when E-Invoice is enabled")