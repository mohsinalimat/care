import frappe

def execute():
    frappe.db.sql("UPDATE `tabOrder Receiving` SET status = 'Submitted' where docstatus = 1")
    frappe.db.sql("UPDATE `tabOrder Receiving` SET status = 'Cancelled' where docstatus = 2")