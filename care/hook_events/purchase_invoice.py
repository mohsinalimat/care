
import frappe
from frappe import _

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