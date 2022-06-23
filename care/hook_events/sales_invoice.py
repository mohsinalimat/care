import frappe
from frappe import _
from frappe.utils import nowdate, now
from care.hook_events.util import round_amount_by_2p5_diff
import requests

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

def validate_cost_center(doc, method):
    if not doc.cost_center:
        frappe.throw(_("Cost center is Mandatory in Accounting dimensions"))


@frappe.whitelist()
def create_franchise_inv(doc_name):
    doc = frappe.get_doc("Sales Invoice", doc_name)
    create_franchise_invoice(doc, None)

def create_franchise_invoice(inv, method):
    if inv.is_franchise_inv:
        f_w_data = frappe.get_value("Franchise Item", {'warehouse': inv.set_warehouse, 'enable': 1}, "name")
        if f_w_data:
            f_w_doc = frappe.get_doc("Franchise Item", f_w_data)
            if not f_w_doc.customer:
                frappe.throw("Please set Franchise {0} Supplier in Franchise DocType".format(inv.set_warehouse))
            data = {
                "sales_invoice_ref": inv.name,
                "supplier": f_w_doc.supplier,
                "posting_date": str(inv.posting_date),
                "due_date": str(inv.due_date),
                "company": f_w_doc.company_name,
                "update_stock": 1,
                "set_warehouse": inv.set_warehouse,
                "items": []
            }
            itm_lst = data['items']
            for res in inv.items:
                itm_lst.append({
                    "item_code": res.item_code,
                    "warehouse": res.warehouse,
                    "qty": res.qty,
                    "received_qty": res.qty,
                    "rate": res.rate,
                    "uom": res.uom,
                    "stock_Uom": res.stock_uom,
                    "margin_type": res.margin_type,
                    "discount_percentage": res.discount_percentage,
                    "discount_amount": res.discount_amount
                })

            url = str(f_w_doc.url) + "/api/resource/Purchase Invoice"
            api_key = f_w_doc.api_key
            api_secret = f_w_doc.api_secret
            headers = {
                'Authorization': 'token ' + str(api_key) + ':' + str(api_secret)
            }
            payload = dict({"data": data})
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                frappe.log_error(title="Franchise Invoice Creation Error", message=response.json())
                frappe.msgprint(
                    "Franchise invoice created on <b><a href='{0}' target='_blank'>{0}</a></b>".format(f_w_doc.url),
                    indicator='Green', alert=True)
                inv.franchise_inv_gen = 1
                inv.db_update()
            else:
                frappe.log_error(title="Franchise Invoice Creation Error", message=response.json())
                frappe.msgprint("Error Log Generated", indicator='red', alert=True)



