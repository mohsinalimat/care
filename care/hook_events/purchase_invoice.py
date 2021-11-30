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