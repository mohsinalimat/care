import frappe
from frappe.utils import nowdate

def updated_item_amendment_summary(doc, method):
    for res in doc.items:
        if not frappe.get_value('Invoice Item Amendment Summary', {'parent': doc.name, 'item_code':res.item_code, 'qty': res.qty}, ['name']):
            doc.append('item_amendment',
                {'item_code': res.item_code,
                    'item_name': res.item_name,
                    'qty': res.qty,
                    'amend_date': nowdate(),
                    'amend_by': frappe.session.user
                }
            )