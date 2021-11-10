import frappe
from erpnext.stock.get_item_details import get_conversion_factor
import json

@frappe.whitelist()
def get_franchise_order(supplier, warehouse=None, order_uom=None):
    if supplier:
        supplier = json.loads(supplier)
    else:
        return {}
    w_lst = ["axop123"]

    wr_doc = frappe.get_doc("Warehouse", warehouse)
    w_lst.append(warehouse)

    if wr_doc.is_group:
        child_wr = frappe.get_list("Warehouse", filters={'parent_warehouse': wr_doc.name}, fields='*')
        for r in child_wr:
            w_lst.append(r.name)

    query = """select i.name as item_code,
            i.item_name,
            i.description,
            i.brand,
            idf.default_supplier,
            ird.warehouse,
            ird.warehouse_reorder_level,
            ird.warehouse_reorder_qty,
            ird.optimum_level,
            b.actual_qty,
            i.stock_uom,
            i.last_purchase_rate,
            0 as conversion_factor
            from `tabItem` i
            inner join `tabItem Default` idf on idf.parent = i.name
            inner  join `tabItem Reorder` ird on ird.parent = i.name
            left join `tabBin` b on b.item_code = i.name and b.warehouse = ird.warehouse
            where
            idf.default_supplier is not null
            and ird.warehouse is not null
            and i.is_stock_item = 1
            and i.has_variants = 0
            and i.disabled = 0
            and ird.warehouse_reorder_level > 0
            and ird.warehouse_reorder_qty > 0
            and ird.optimum_level > 0
            and (b.actual_qty <= ird.warehouse_reorder_level or b.actual_qty is null)
            and idf.default_supplier in {0}""".format(tuple(supplier))
    if warehouse:
        query += """ and ird.warehouse in {0}""".format(tuple(w_lst))
    query += " order by idf.default_supplier, ird.warehouse, i.name"
    item_details = frappe.db.sql(query, as_dict=True)
    for res in item_details:
        conversion_factor = 1
        conversion = get_conversion_factor(res.item_code, order_uom)
        if conversion:
            conversion_factor = conversion['conversion_factor']
        res['conversion_factor'] = conversion_factor
    return item_details
