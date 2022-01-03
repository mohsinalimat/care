import frappe
from frappe.utils import nowdate, now
from care.hook_events.util import round_amount_by_2p5_diff

def updated_item_amendment_summary(doc, method):
    for res in doc.items:
        if not frappe.get_value('Invoice Item Amendment Summary', {'parent': doc.name, 'item_code':res.item_code, 'qty': res.qty}, ['name']):
            doc.append('item_amendment',
                {'item_code': res.item_code,
                    'item_name': res.item_name,
                    'qty': res.qty,
                    'amend_date': now(),
                    'amend_by': frappe.session.user
                }
            )

def apply_additional_discount(doc, method):
    if doc.docstatus == 0:
        doc.discount_amount = round_amount_by_2p5_diff(doc.grand_total)

def disable_rounded_total(doc, method):
    doc.disable_rounded_total = 1