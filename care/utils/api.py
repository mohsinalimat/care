import frappe
from frappe.utils import nowdate, getdate
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
            and (b.actual_qty < ird.warehouse_reorder_level or b.actual_qty is null)
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

@frappe.whitelist()
def set_account(accounts):
    if accounts:
        acc = json.loads(accounts)
        for res in acc:
            try:
                company = frappe.defaults.get_defaults().company
                if res.get('parent_account'):
                    if not frappe.db.exists("Account", res.get('parent_account')):
                        p_acc = res.get('parent_account').split(" - ")
                        abbr = frappe.get_cached_value("Company", company, ["abbr"], as_dict=True)
                        p_acc[len(p_acc)-1] = abbr.abbr
                        parent = " - ".join(p_acc)
                        res['parent_account'] = parent
                frappe.get_doc(res).insert(ignore_permissions=True, ignore_mandatory=True)
                frappe.db.commit()
            except Exception as e:
                frappe.log_error(title="Creating Account Error", message=e)
                continue

@frappe.whitelist()
def set_item_group(groups):
    if groups:
        group = json.loads(groups)
        for res in group:
            try:
                frappe.get_doc(res).insert(ignore_permissions=True, ignore_mandatory=True)
                frappe.db.commit()
            except Exception as e:
                frappe.log_error(title="Creating Item Group Error", message=e)
                continue

@frappe.whitelist()
def set_item_brand(brands):
    if brands:
        brand = json.loads(brands)
        for res in brand:
            try:
                frappe.get_doc(res).insert(ignore_permissions=True, ignore_mandatory=True)
                frappe.db.commit()
            except Exception as e:
                frappe.log_error(title="Creating Brand Error", message=e)
                continue

@frappe.whitelist()
def set_item_uom(uoms):
    if uoms:
        uom = json.loads(uoms)
        for res in uom:
            try:
                frappe.get_doc(res).insert(ignore_permissions=True, ignore_mandatory=True)
                frappe.db.commit()
            except Exception as e:
                frappe.log_error(title="Creating UOM Error", message=e)
                continue

@frappe.whitelist()
def set_manufacturer(manufacturers):
    if manufacturers:
        manufacturer = json.loads(manufacturers)
        for res in manufacturer:
            try:
                frappe.get_doc(res).insert(ignore_permissions=True, ignore_mandatory=True)
                frappe.db.commit()
            except Exception as e:
                frappe.log_error(title="Creating Manufacturer Error", message=e)
                continue

@frappe.whitelist()
def set_supplier_group(supp_groups):
    if supp_groups:
        supp_group = json.loads(supp_groups)
        for res in supp_group:
            try:
                frappe.get_doc(res).insert(ignore_permissions=True, ignore_mandatory=True)
                frappe.db.commit()
            except Exception as e:
                frappe.log_error(title="Creating Supplier Group Error", message=e)
                continue

@frappe.whitelist()
def set_supplier(suppliers):
    if suppliers:
        supplier = json.loads(suppliers)
        for res in supplier:
            try:
                exist_supp = frappe.db.get_value("Supplier", {"supplier_name": res.get('supplier_name')}, "name")
                if not frappe.db.exists("Supplier", res.get('name')) and not exist_supp:
                    frappe.get_doc(res).insert(ignore_permissions=True, ignore_mandatory=True)
                    frappe.db.commit()
            except Exception as e:
                frappe.log_error(title="Creating Supplier Error", message=e)
                continue


@frappe.whitelist()
def set_item(items):
    if items:
        item = json.loads(items)
        company = frappe.defaults.get_defaults().company
        for res in item:
            if res.get('item_defaults'):
                for di in res.get('item_defaults'):
                    di['company'] = company
                    if di.get('default_discount_account'):
                        if not frappe.db.exists("Account", di.get('default_discount_account')):
                            p_acc = di.get('default_discount_account').split(" - ")
                            abbr = frappe.get_cached_value("Company", company, ["abbr"], as_dict=True)
                            p_acc[len(p_acc) - 1] = abbr.abbr
                            account = " - ".join(p_acc)
                            if frappe.db.exists("Account", account):
                                di['default_discount_account'] = account
                            else:
                                di['default_discount_account'] = None

                    if di.get('expense_account'):
                        if not frappe.db.exists("Account", di.get('expense_account')):
                            p_acc = di.get('expense_account').split(" - ")
                            abbr = frappe.get_cached_value("Company", company, ["abbr"], as_dict=True)
                            p_acc[len(p_acc) - 1] = abbr.abbr
                            account = " - ".join(p_acc)
                            if frappe.db.exists("Account", account):
                                di['expense_account'] = account
                            else:
                                di['expense_account'] = None

                    if di.get('income_account'):
                        if not frappe.db.exists("Account", di.get('income_account')):
                            p_acc = di.get('income_account').split(" - ")
                            abbr = frappe.get_cached_value("Company", company, ["abbr"], as_dict=True)
                            p_acc[len(p_acc) - 1] = abbr.abbr
                            account = " - ".join(p_acc)
                            if frappe.db.exists("Account", account):
                                di['income_account'] = account
                            else:
                                di['income_account'] = None

                    if di.get('default_supplier'):
                        supplier = None
                        if di.get('supplier_name'):
                            supplier = frappe.db.get_value("Supplier", {"supplier_name": di.get('supplier_name')}, "name")

                        if frappe.db.exists("Supplier", di.get('default_supplier')):
                            supplier = di.get('default_supplier')
                        di['default_supplier'] = supplier
            try:
                if frappe.db.exists("Item", res.get('item_code')):
                    item_doc = frappe.get_doc("Item", res.get('item_code'))
                    item_doc.update(res)
                    item_doc.flags.ignore_permissions = True
                    item_doc.flags.ignore_mandatory = True
                    item_doc.flags.ignore_if_duplicate = True
                    item_doc.save()
                else:
                    frappe.get_doc(res).insert(ignore_permissions=True, ignore_mandatory=True)
                    frappe.db.commit()
            except Exception as e:
                frappe.log_error(title="Creating Item or Updating Error", message=e)
                continue

@frappe.whitelist()
def set_item_price(item_prices):
    if item_prices:
        item_price = json.loads(item_prices)
        for res in item_price:
            try:
                existing_price = frappe.db.get_value("Item Price", {"item_code": res.get('item_code'),
                                                    "buying": res.get('buying'),
                                                    "selling": res.get('selling')
                                                    }, "name")
                if existing_price:
                    itm_price = frappe.get_doc("Item Price", existing_price)
                    itm_price.update(res)
                    itm_price.flags.ignore_permissions = True
                    itm_price.flags.ignore_mandatory = True
                    itm_price.flags.ignore_if_duplicate = True
                    itm_price.save()
                else:
                    frappe.get_doc(res).insert(ignore_permissions=True, ignore_mandatory=True)
                    frappe.db.commit()
            except Exception as e:
                frappe.log_error(title="Creating Item Price Error", message=e)
                continue

@frappe.whitelist()
def set_price_rule(rules):
    if rules:
        rules = json.loads(rules)
        for res in rules:
            supplier = None
            if res.get('supplier_name'):
                supplier = frappe.db.get_value("Supplier", {"supplier_name": res.get('supplier_name')}, "name")

            if frappe.db.exists("Supplier", res.get('supplier')):
                supplier = res.get('supplier')
            res['supplier'] = supplier
            try:
                if frappe.db.exists("Pricing Rule", res.get('name')):
                    pricing_rule = frappe.get_doc("Pricing Rule", res.get('name'))
                    pricing_rule.update(res)
                    pricing_rule.flags.ignore_permissions = True
                    pricing_rule.flags.ignore_mandatory = True
                    pricing_rule.flags.ignore_if_duplicate = True
                    pricing_rule.save()
                else:
                    frappe.get_doc(res).insert(ignore_permissions=True, ignore_mandatory=True)
                    frappe.db.commit()
            except Exception as e:
                frappe.log_error(title="Creating Pricing rule Error", message=e)
                continue

@frappe.whitelist()
def create_purchase_invoice(invoice):
    if invoice:
        invoice = json.loads(invoice)
        submit_invoice = invoice.get('submit_invoice')
        doc = frappe.get_doc(invoice)
        doc.set_missing_values()
        doc.insert(ignore_permissions=True, ignore_mandatory=True)
        frappe.db.commit()
        if submit_invoice:
            try:
                doc.submit()
            except Exception as e:
                pass
