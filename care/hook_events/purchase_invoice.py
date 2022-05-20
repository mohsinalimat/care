import json

import frappe
from frappe import _
from frappe.utils import add_days, add_months, cint, cstr, flt, getdate
from frappe.model.mapper import get_mapped_doc
from erpnext.stock.get_item_details import get_item_price, check_packing_list
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import get_returned_qty_map, get_invoiced_qty_map
from erpnext.controllers.accounts_controller import get_taxes_and_charges

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
    if doc.items and not doc.update_buying_price:
        for res in doc.items:
            if res.item_code:
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


def updated_price_list(doc, method):
    if doc.update_buying_price or doc.update_selling_price:
        for res in doc.items:
            if doc.update_buying_price and res.rate != res.price_list_rate:
                buying_price_list = frappe.get_value("Item Price", {'item_code': res.item_code, 'price_list': doc.buying_price_list,'buying': 1}, ['name'])
                if buying_price_list:
                    item_price = frappe.get_doc("Item Price", buying_price_list)
                    item_price.price_list_rate = res.rate / res.conversion_factor
                    item_price.save(ignore_permissions=True)
            if doc.update_selling_price and res.selling_price_list_rate != res.base_selling_price_list_rate:
                selling_price_list = frappe.get_value("Item Price", {'item_code': res.item_code, 'price_list': doc.base_selling_price_list, 'selling': 1}, ['name'])
                if selling_price_list:
                    item_price = frappe.get_doc("Item Price", selling_price_list)
                    item_price.price_list_rate = res.selling_price_list_rate / res.conversion_factor
                    item_price.save(ignore_permissions=True)

@frappe.whitelist()
def make_purchase_invoice(source_name, target_doc=None):
    from erpnext.accounts.party import get_payment_terms_template

    doc = frappe.get_doc('Purchase Receipt', source_name)
    returned_qty_map = get_returned_qty_map(source_name)
    invoiced_qty_map = get_invoiced_qty_map(source_name)
    count = 1

    def set_missing_values(source, target):
        if len(target.get("items")) == 0:
            frappe.throw(_("All items have already been Invoiced/Returned"))
        cost_center = frappe.get_value('Company', source.get("company"), "cost_center")

        doc = frappe.get_doc(target)
        doc.payment_terms_template = get_payment_terms_template(source.supplier, "Supplier", source.company)
        # if doc.taxes_and_charges and not doc.taxes:
        #     taxes = get_taxes_and_charges('Purchase Taxes and Charges Template', doc.taxes_and_charges)
        #     for tax in taxes:
        #         doc.append('taxes', tax)
        doc.cost_center = cost_center
        doc.run_method("onload")
        doc.run_method("set_missing_values")
        doc.run_method("calculate_taxes_and_totals")
        doc.set_payment_schedule()

    def update_item(source_doc, target_doc, source_parent):
        target_doc.qty, returned_qty = get_pending_qty(source_doc)
        if frappe.db.get_single_value("Buying Settings", "bill_for_rejected_quantity_in_purchase_invoice"):
            target_doc.rejected_qty = 0
        target_doc.stock_qty = flt(target_doc.qty) * flt(target_doc.conversion_factor, target_doc.precision("conversion_factor"))
        returned_qty_map[source_doc.name] = returned_qty

    def get_item_data_taxes(source_doc, target_doc, source_parent):
        wr = source_doc.set_warehouse if source_doc.set_warehouse else ""
        account = frappe.get_value('Company', source_doc.get("company"), "stock_received_but_not_billed")
        cost_center = frappe.get_value('Company', source_doc.get("company"), "cost_center")
        target_doc.append("items",{
            'item_name': source_doc.name + "-" + wr,
            'qty': 1,
            'uom': 'Pack',
            'rate': source_doc.total,
            'purchase_receipt': source_doc.name,
            'expense_account': account,
            'cost_center': cost_center
        })
        # target_doc.set("taxes", [])
        for res in source_doc.taxes:
            tax_dict = res.as_dict()
            tax_dict.pop('name')
            tax_dict.pop('idx')
            tax_dict.pop('owner')
            tax_dict.pop('creation')
            tax_dict.pop('modified')
            tax_dict.pop('modified_by')
            tax_dict.pop('parent')
            tax_dict.pop('parentfield')
            tax_dict.pop('parenttype')
            tax_dict.pop('total')
            tax_dict.pop('base_tax_amount')
            tax_dict.pop('base_tax_amount_after_discount_amount')
            tax_dict.pop('base_total')
            tax_dict.pop('tax_amount_after_discount_amount')
            if tax_dict['charge_type'] == 'On Net Total':
                tax_dict['charge_type'] = 'Actual'
            not_present = 1
            if 'taxes' in target_doc.as_dict().keys():
                for t_tax in target_doc.taxes:
                    if t_tax.charge_type == tax_dict.charge_type and t_tax.account_head == tax_dict.account_head:
                        if t_tax.rate and tax_dict.rate and t_tax.rate == tax_dict.rate:
                            not_present = 0
                        elif not t_tax.rate and not tax_dict.rate:
                            t_tax.tax_amount = res.tax_amount + (t_tax.tax_amount if t_tax.tax_amount else 0)
                            not_present = 0
                if not_present:
                    target_doc.append("taxes", tax_dict)
            else:
                target_doc.append("taxes", tax_dict)

    def get_pending_qty(item_row):
        qty = item_row.qty
        if frappe.db.get_single_value("Buying Settings", "bill_for_rejected_quantity_in_purchase_invoice"):
            qty = item_row.received_qty
        pending_qty = qty - invoiced_qty_map.get(item_row.name, 0)
        returned_qty = flt(returned_qty_map.get(item_row.name, 0))
        if returned_qty:
            if returned_qty >= pending_qty:
                pending_qty = 0
                returned_qty -= pending_qty
            else:
                pending_qty -= returned_qty
                returned_qty = 0
        return pending_qty, returned_qty


    doclist = get_mapped_doc("Purchase Receipt", source_name,	{
        "Purchase Receipt": {
            "doctype": "Purchase Invoice",
            "field_map": {
                "supplier_warehouse":"supplier_warehouse",
                "is_return": "is_return",
                "bill_date": "bill_date"
            },
            "validation": {
                "docstatus": ["=", 1],
            },
            "postprocess": get_item_data_taxes
        },
        # "Purchase Receipt Item": {
        #     "doctype": "Purchase Invoice Item",
        #     "field_map": {
        #         "name": "pr_detail",
        #         "parent": "purchase_receipt",
        #         "purchase_order_item": "po_detail",
        #         "purchase_order": "purchase_order",
        #         "is_fixed_asset": "is_fixed_asset",
        #         "asset_location": "asset_location",
        #         "asset_category": 'asset_category'
        #     },
        #     "postprocess": update_item,
        #     "filter": lambda d: get_pending_qty(d)[0] <= 0 if not doc.get("is_return") else get_pending_qty(d)[0] > 0
        # },
        "Purchase Taxes and Charges": {
            "doctype": "Purchase Taxes and Charges",
            "add_if_empty": True
        }
    }, target_doc, set_missing_values)

    return doclist


def update_billing_percentage(doc,method):
    for res in doc.items:
        if res.purchase_receipt:
            pr_doc = frappe.get_doc("Purchase Receipt", res.purchase_receipt)
            pr_doc.db_set("per_billed", 100)
            pr_doc.load_from_db()
            pr_doc.set_status(update=True)
            pr_doc.notify_update()


def rev_update_billing_percentage(doc,method):
    for res in doc.items:
        if res.purchase_receipt:
            pr_doc = frappe.get_doc("Purchase Receipt", res.purchase_receipt)
            pr_doc.db_set("per_billed", 0)
            pr_doc.load_from_db()
            pr_doc.set_status(update=True)
            pr_doc.notify_update()