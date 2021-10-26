
import frappe
from frappe import _

def update_md_status(doc, method):
    lst = []
    for res in doc.items:
        if res.material_demand_item and res.material_demand:
            if frappe.db.exists("Material Demand Item", res.material_demand_item):
                mdi = frappe.get_doc("Material Demand Item", res.material_demand_item)
                exit_qty = float(mdi.ordered_qty)
                mdi.ordered_qty = exit_qty + float(res.qty)
                mdi.db_update()

            if res.material_demand not in lst:
                lst.append(res.material_demand)

    for mrd in lst:
        md = frappe.get_doc("Material Demand", mrd)
        total_qty = 0
        for r in md.items:
            total_qty += r.ordered_qty
        per = round((total_qty / md.total_qty) * 100, 2)
        md.per_ordered = per
        if per < 99.99:
            md.status = "Partially Ordered"
        else:
            md.status = "Ordered"
        md.db_update()

def cancel_update_md_status(doc, method):
    lst = []
    for res in doc.items:
        if res.material_demand_item and res.material_demand:
            if frappe.db.exists("Material Demand Item", res.material_demand_item):
                mdi = frappe.get_doc("Material Demand Item", res.material_demand_item)
                exit_qty = float(mdi.ordered_qty)
                mdi.ordered_qty = exit_qty - float(res.qty)
                mdi.db_update()
            if res.material_demand not in lst:
                lst.append(res.material_demand)

    for mrd in lst:
        md = frappe.get_doc("Material Demand", mrd)
        total_qty = 0
        for r in md.items:
            total_qty += r.ordered_qty
        per = round((total_qty / md.total_qty) * 100, 2)
        md.per_ordered = per
        if per < 99.99:
            md.status = "Partially Ordered"
        else:
            md.status = "Ordered"
        md.db_update()
