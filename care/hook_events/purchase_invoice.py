import json

import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, cstr, flt, getdate
from erpnext.stock.get_item_details import get_item_price, check_packing_list

def update_p_r_c_tool_status(doc, method):
    if doc.purchase_invoice_creation_tool:
        prc_doc = frappe.get_doc("Purchase Invoice Creation Tool", doc.purchase_invoice_creation_tool)
        prc_doc.status = "Invoice Created"
        prc_doc.db_update()

def cancel_update_p_r_c_tool_status(doc, method):
    if doc.purchase_invoice_creation_tool:
        prc_doc = frappe.get_doc("Purchase Invoice Creation Tool", doc.purchase_invoice_creation_tool)
        prc_doc.status = "Success"
        prc_doc.db_update()


@frappe.whitelist()
def delete_purchase_inv_cr_tol_item():
    frappe.db.sql("delete from `tabPurchase Invoice Creation Tool Item`")


def update_md_status(doc, method):
    lst = []
    for res in doc.items:
        if res.material_demand_item and res.material_demand:
            if frappe.db.exists("Material Demand Item", res.material_demand_item):
                mdi = frappe.get_doc("Material Demand Item", res.material_demand_item)
                exit_qty = float(mdi.received_qty)
                mdi.received_qty = exit_qty + float(res.qty)
                mdi.db_update()

            if res.material_demand not in lst:
                lst.append(res.material_demand)

    for mrd in lst:
        md = frappe.get_doc("Material Demand", mrd)
        total_qty = 0
        for r in md.items:
            total_qty += r.received_qty
        per = round((total_qty / md.total_qty) * 100, 2)
        md.per_received = per
        if per < 99.99:
            md.status = "Partially Received"
        else:
            md.status = "Received"
        md.db_update()

def cancel_update_md_status(doc, method):
    lst = []
    for res in doc.items:
        if res.material_demand_item and res.material_demand:
            if frappe.db.exists("Material Demand Item", res.material_demand_item):
                mdi = frappe.get_doc("Material Demand Item", res.material_demand_item)
                exit_qty = float(mdi.received_qty)
                mdi.received_qty = exit_qty - float(res.qty)
                mdi.db_update()

            if res.material_demand not in lst:
                lst.append(res.material_demand)

    for mrd in lst:
        md = frappe.get_doc("Material Demand", mrd)
        total_qty = 0
        for r in md.items:
            total_qty += r.received_qty
        per = round((total_qty / md.total_qty) * 100, 2)
        md.per_received = per
        if per < 99.99:
            md.status = "Partially Received"
        else:
            md.status = "Received"
        md.db_update()

def validate_cost_center(doc, method):
    if not doc.cost_center:
        frappe.throw(_("Cost center is Mandatory in Accounting dimensions"))


@frappe.whitelist()
def get_price_list_rate_for(item_code, args):
    """
        :param customer: link to Customer DocType
        :param supplier: link to Supplier DocType
        :param price_list: str (Standard Buying or Standard Selling)
        :param item_code: str, Item Doctype field item_code
        :param qty: Desired Qty
        :param transaction_date: Date of the price
    """
    args = frappe._dict(json.loads(args))
    item_price_args = {
            "item_code": item_code,
            "price_list": args.get('price_list'),
            "customer": args.get('customer'),
            "supplier": args.get('supplier'),
            "uom": args.get('uom'),
            "transaction_date": args.get('transaction_date'),
            "posting_date": args.get('posting_date'),
            "batch_no": args.get('batch_no')
    }

    item_price_data = 0
    price_list_rate = get_item_price(item_price_args, item_code)
    if price_list_rate:
        desired_qty = args.get("qty")
        if desired_qty and check_packing_list(price_list_rate[0][0], desired_qty, item_code):
            item_price_data = price_list_rate
    else:
        for field in ["customer", "supplier"]:
            del item_price_args[field]

        general_price_list_rate = get_item_price(item_price_args, item_code,
            ignore_party=args.get("ignore_party"))

        if not general_price_list_rate and args.get("uom") != args.get("stock_uom"):
            item_price_args["uom"] = args.get("stock_uom")
            general_price_list_rate = get_item_price(item_price_args, item_code, ignore_party=args.get("ignore_party"))

        if general_price_list_rate:
            item_price_data = general_price_list_rate

    if item_price_data:
        if item_price_data[0][2] == args.get("uom"):
            return item_price_data[0][1]
        elif not args.get('price_list_uom_dependant'):
            return flt(item_price_data[0][1] * flt(args.get("conversion_factor", 1)))
        else:
            return item_price_data[0][1]

def validate_price_and_rate(doc, method):
    if doc.items:
        for res in doc.items:
            if res.price_list_rate - 1 <= res.rate <= res.price_list_rate + 1:
                pass
            else:
                frappe.throw(_("Item <b>{0}:{1}</b> Price List Rate and Rate did not match in row {2}.".format(res.item_code,res.item_name,res.idx)))


@frappe.whitelist()
def make_franchise_purchase_invoice(doc):
    doc = frappe.get_doc("Purchase Invoice", doc)
    create_franchise_purchase_invoice(doc, None)

@frappe.whitelist()
def un_check_franchise_inv_generated(doc, method):
    doc.franchise_inv_generated = 0

@frappe.whitelist()
def create_franchise_purchase_invoice(doc, method):
    import requests
    if doc.purchase_request and doc.set_warehouse and not doc.franchise_inv_generated:
        w_doc = frappe.get_doc("Warehouse", doc.set_warehouse)
        if w_doc.is_franchise:
            if not w_doc.company_name:
                frappe.throw("Please set company name in franchise Warehouse.")

            if w_doc.url and w_doc.api_key and w_doc.api_secret:
                data = {
                    "name": doc.name,
                    "supplier": doc.supplier,
                    "posting_date": str(doc.posting_date),
                    "due_date": str(doc.due_date),
                    "company": w_doc.company_name,
                    "update_stock": 1,
                    "set_warehouse": doc.set_warehouse,
                    "items": []
                }
                itm_lst = data['items']
                for res in doc.items:
                    itm_lst.append({
                            "item_code": res.item_code,
                            "warehouse": res.warehouse,
                            "qty": res.qty,
                            "received_qty": res.qty,
                            "rate": res.rate,
                            "expense_account": res.expense_account,
                            "cost_center": res.cost_center,
                            "uom": res.uom,
                            "stock_Uom": res.stock_uom,
                            "margin_type": res.margin_type,
                            "discount_percentage": res.discount_percentage,
                            "discount_amount": res.discount_amount
                        })
                try:
                    url = str(w_doc.url) + "/api/resource/Purchase Invoice"
                    api_key = w_doc.api_key
                    api_secret = w_doc.api_secret
                    headers = {
                        'Authorization': 'token ' + str(api_key) + ':' + str(api_secret)
                    }
                    payload = dict({"data": data})
                    response = requests.post(url, headers=headers, json=payload)
                    if response.status_code == 200:
                        frappe.log_error(title="Franchise Invoice Creation Error", message=response.json())
                        frappe.msgprint("Franchise invoice created on <b><a href='{0}' target='_blank'>{0}</a></b>".format(w_doc.url), indicator='Green', alert=True)
                        doc.franchise_inv_generated = 1
                        doc.db_update()
                    else:
                        frappe.log_error(title="Franchise Invoice Creation Error", message=response.json())
                        frappe.msgprint("Error Log Generated", indicator='red', alert=True)

                except Exception as e:
                    frappe.log_error(title="Franchise Invoice Creation Error", message=e)
                    frappe.msgprint("Error Log Generated", indicator='red', alert=True)

            else:
                frappe.log_error(title="Franchise configuration messing Error", message=w_doc.as_dict())
                frappe.msgprint("Error Log Generated", indicator='red', alert=True)


