from . import __version__ as app_version

app_name = "care"
app_title = "Care"
app_publisher = "RF"
app_description = "Auto perform pos invoice"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "sales@resourcesfactor.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/care/css/care.css"
app_include_js = "/assets/care/js/data_import_tools1.min.js"

# include js, css files in header of web template
# web_include_css = "/assets/care/css/care.css"
# web_include_js = "/assets/care/js/care.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "care/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Payment Entry": "public/js/payment_entry.js",
    "Purchase Invoice": "public/js/purchase_invoice.js",
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

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

# Installation
# ------------

# before_install = "care.install.before_install"
# after_install = "care.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "care.notifications.get_notification_config"

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
    "Purchase Order": {
        "on_submit": "care.hook_events.purchase_order.update_md_status",
        "on_cancel": "care.hook_events.purchase_order.cancel_update_md_status",
    },
    # "Purchase Receipt": {
    #     "on_submit": "care.hook_events.purchase_receipt.update_md_status",
    #     "on_cancel": "care.hook_events.purchase_receipt.cancel_update_md_status",
    # },
    "Purchase Invoice": {
        "on_submit": ["care.hook_events.purchase_invoice.update_p_r_c_tool_status",
                      "care.hook_events.purchase_invoice.update_md_status",
                      "care.hook_events.purchase_invoice.create_franchise_purchase_invoice",
                      "care.hook_events.purchase_invoice.updated_price_list"],
        "on_cancel": ["care.hook_events.purchase_invoice.cancel_update_p_r_c_tool_status",
                     "care.hook_events.purchase_invoice.cancel_update_md_status"],
        "before_submit": ["care.hook_events.purchase_invoice.validate_cost_center",
                          "care.hook_events.purchase_invoice.validate_price_and_rate"],
        "before_insert": "care.hook_events.purchase_invoice.un_check_franchise_inv_generated"
    },
    # "Sales Invoice": {
    #     "before_submit": ["care.hook_events.purchase_invoice.validate_cost_center"]
    # },
    "Payment Entry": {
        "validate": ["care.hook_events.payment_entry.set_out_grand_total"]
    }
}

# Scheduled Tasks
# ---------------

scheduler_events = {
    "hourly": ["care.hook_events.override_pos_closing.execute_pos_invoices"],
    "daily": ["care.hook_events.purchase_invoice.delete_purchase_inv_cr_tol_item"]
}

# Testing
# -------

# before_tests = "care.install.before_tests"

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
	"erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry.get_pos_invoices": "care.hook_events.override_pos_closing.get_pos_invoices"
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "care.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

override_doctype_class = {
    'POS Closing Entry': 'care.hook_events.override_pos_closing.OverridePOSClosingEntry',
    'POS Invoice Merge Log': 'care.hook_events.override_pos_merge_log.OverridePOSInvoiceMergeLog'
}

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

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"care.auth.validate"
# ]

