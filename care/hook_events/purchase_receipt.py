
import frappe
from frappe.utils import flt
from erpnext.controllers.taxes_and_totals import get_itemised_tax_breakup_data

def update_p_r_c_tool_status(doc, method):
    if doc.purchase_invoice_creation_tool:
        prc_doc = frappe.get_doc("Purchase Invoice Creation Tool", doc.purchase_invoice_creation_tool)
        prc_doc.status = "Receipt Created"
        prc_doc.db_update()

def cancel_update_p_r_c_tool_status(doc, method):
    if doc.purchase_invoice_creation_tool:
        prc_doc = frappe.get_doc("Purchase Invoice Creation Tool", doc.purchase_invoice_creation_tool)
        prc_doc.status = "Success"
        prc_doc.db_update()

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


def calculate_item_level_tax_breakup(doc, method):
    if doc:
        itemised_tax, itemised_taxable_amount = get_itemised_tax_breakup_data(doc)
        if itemised_tax:
            for res in doc.items:
                total = 0
                if res.item_code in itemised_tax.keys():
                    for key in itemised_tax[res.item_code].keys():
                        if 'Sales Tax' in key:
                            res.sales_tax = flt(itemised_tax[res.item_code][key]['tax_amount']) if itemised_tax[res.item_code][key]['tax_amount'] else 0
                            total += flt(res.sales_tax)
                        if 'Further Tax' in key:
                            res.further_tax = flt(itemised_tax[res.item_code][key]['tax_amount']) if itemised_tax[res.item_code][key]['tax_amount'] else 0
                            total += flt(res.further_tax)
                        if 'Advance Tax' in key:
                            res.advance_tax = flt(itemised_tax[res.item_code][key]['tax_amount'])if itemised_tax[res.item_code][key]['tax_amount'] else 0
                res.total_includetaxes = flt(res.sales_tax + res.further_tax + res.advance_tax) + res.amount
        else:
            for res in doc.items:
                res.sales_tax = res.further_tax = res.advance_tax = res.total_includetaxes = 0
