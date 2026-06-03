from . import __version__ as app_version

app_name = "einvoice"
app_title = "E Invoice"
app_publisher = "Ruben Jara"
app_description = "Electronic Invoice System"
app_email = "ruben-jara@live.com"
app_license = "gpl-3.0"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/einvoice/css/einvoice.css"
# app_include_js = "/assets/einvoice/js/einvoice.js"

# include js, css files in header of web template
# web_include_css = "/assets/einvoice/css/einvoice.css"
# web_include_js = "/assets/einvoice/js/einvoice.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "einvoice/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Sales Invoice": "e_invoice/public/js/sales_invoice_combined.js",
    "Purchase Invoice": "e_invoice/public/js/purchase_invoice.js",
    "Delivery Note": "e_invoice/public/js/delivery_note.js",
    "Address": "e_invoice/doctype/address/address.js"
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# include python in doctype views
doctype_python = {
    "Address": "e_invoice.doctype.address.address"
}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
#	"methods": "einvoice.utils.jinja_methods",
#	"filters": "einvoice.utils.jinja_filters"
# }

# Installation
# ------------

before_install = "einvoice.e_invoice.before_install.before_install"
after_install = "einvoice.e_invoice.install.after_install"

# Uninstallation
# ------------

before_uninstall = "einvoice.e_invoice.install.before_uninstall"
# after_uninstall = "einvoice.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "einvoice.utils.before_app_install"
# after_app_install = "einvoice.utils.after_app_install"

# Runs after each bench migrate (including Docker startup)
after_migrate = "einvoice.e_invoice.helpers.naming_helper.configure_7_digit_naming_series"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "einvoice.utils.before_app_uninstall"
# after_app_uninstall = "einvoice.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "einvoice.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Address": {
        "validate": "einvoice.e_invoice.utils.address_validation.validate_address_sifen",
    },
    "Customer": {
        "before_insert": "einvoice.e_invoice.doctype.customer.customer.before_insert",
        "validate": "einvoice.e_invoice.doctype.customer.customer.validate",
    },
    "Supplier": {
        "before_insert": "einvoice.e_invoice.doctype.supplier.supplier.before_insert",
    },
    "Sales Invoice": {
        "validate": [
            "einvoice.e_invoice.utils.api_client.asignar_numero_control",
            "einvoice.e_invoice.utils.api_client.validar_campos_sifen",
        ],
        "on_cancel": "einvoice.e_invoice.doc_events.sales_invoice.on_cancel",
    },
    "Purchase Invoice": {
        "validate": [
            "einvoice.e_invoice.utils.api_client.asignar_numero_control",
            "einvoice.e_invoice.utils.api_client.validar_campos_sifen",
        ],
        "on_cancel": "einvoice.e_invoice.doc_events.purchase_invoice.on_cancel",
    },
    "Delivery Note": {
        "validate": [
            "einvoice.e_invoice.utils.api_client.asignar_numero_control",
            "einvoice.e_invoice.utils.api_client.validar_campos_sifen",
        ],
        "on_cancel": "einvoice.e_invoice.doc_events.delivery_note.on_cancel",
    },
    "Vehicle": {
        "validate": "einvoice.e_invoice.doctype.vehicle.vehicle.validate",
    }
    # "Sales Invoice": {
    #     "on_submit": "einvoice.e_invoice.doc_events.sales_invoice.generate_einvoice_manually",
    # }
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"einvoice.tasks.all"
# 	],
# 	"daily": [
# 		"einvoice.tasks.daily"
# 	],
# 	"hourly": [
# 		"einvoice.tasks.hourly"
# 	],
# 	"weekly": [
# 		"einvoice.tasks.weekly"
# 	],
# 	"monthly": [
# 		"einvoice.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "einvoice.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "einvoice.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "einvoice.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["einvoice.utils.before_request"]
# after_request = ["einvoice.utils.after_request"]

# Job Events
# ----------
# before_job = ["einvoice.utils.before_job"]
# after_job = ["einvoice.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Doctype Definitions
# ---------------------

# override_doctype_dashboards = {
# 	"Sales Invoice": "einvoice.e_invoice.dashboard_overrides.sales_invoice_dashboard"
# }

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"einvoice.auth.validate"
# ]

# Translation
# --------------------------------

# override_whitelisted_methods = {
#     'einvoice.e_invoice.doc_events.sales_invoice.trigger_einvoice_generation': 'einvoice.e_invoice.doc_events.sales_invoice.trigger_einvoice_generation',
#     'einvoice.e_invoice.doc_events.sales_invoice.test_einvoice_connection': 'einvoice.e_invoice.doc_events.sales_invoice.test_einvoice_connection',
#     'einvoice.e_invoice.doc_events.sales_invoice.get_einvoice_status': 'einvoice.e_invoice.doc_events.sales_invoice.get_einvoice_status'
# }