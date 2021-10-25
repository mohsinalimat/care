# Copyright (c) 2021, RF and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from erpnext.stock.get_item_details import get_conversion_factor
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.setup.doctype.brand.brand import get_brand_defaults

class PurchaseRequest(Document):

	@frappe.whitelist()
	def get_items(self):
		if not self.suppliers:
			frappe.throw(_("Select suppliers"))
		# if not self.warehouses:
		# 	frappe.throw(_("Select Warehouses"))
		s_lst = ["axop123"]
		w_lst = ["axop123"]
		for res in self.suppliers:
			s_lst.append(res.supplier)

		for res in self.warehouses:
			w_lst.append(res.warehouse)

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
				i.last_purchase_rate
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
				and idf.default_supplier in {0}""".format(tuple(s_lst))
		if self.warehouses:
			query += """ and ird.warehouse in {0}""".format(tuple(w_lst))
		query += " order by idf.default_supplier, ird.warehouse, i.name"
		item_details = frappe.db.sql(query,as_dict=True)
		return item_details

	def on_submit(self):
		if not self.items:
			frappe.throw(_("no Items Found. Please set first"))
		self.make_material_demand()

	def make_material_demand(self):
		if self.items:
			item_details = {}
			for res in self.items:
				key = (res.supplier, res.warehouse)
				item_details.setdefault(key, {"details": []})
				fifo_queue = item_details[key]["details"]
				fifo_queue.append(res)
			if item_details:
				for key in item_details.keys():
					md = frappe.new_doc("Material Demand")
					md.supplier = key[0]
					md.warehouse = key[1]
					md.transaction_date = self.date
					md.schedule_date = self.required_by
					md.company = self.company
					md.purchase_request = self.name
					for d in item_details[key]['details']:
						conversion_factor = 1
						conversion = get_conversion_factor(d.item_code, self.order_uom)
						if conversion:
							conversion_factor = conversion['conversion_factor']

						item_defaults = get_item_defaults(d.item_code, self.company)
						item_group_defaults = get_item_group_defaults(d.item_code, self.company)
						brand_defaults = get_brand_defaults(d.item_code, self.company)
						expense_account = get_default_expense_account(item_defaults, item_group_defaults, brand_defaults)
						cost_center = get_default_cost_center(self,item_defaults, item_group_defaults, brand_defaults)

						md.append("items", {
							"item_code": d.item_code,
							"item_name": d.item_name,
							"brand": d.brand,
							"description": d.item_description,
							"schedule_date": self.required_by,
							"qty": d.order_qty,
							"stock_uom": d.stock_uom,
							"uom": self.order_uom,
							"conversion_factor": conversion_factor,
							"warehouse": key[1],
							"actual_qty": d.avl_qty,
							"rate": d.rate,
							"amount": d.rate * d.order_qty,
							"stock_qty": d.order_qty * conversion_factor,
							"expense_account": expense_account,
							"cost_center": cost_center
						})
					md.insert()



def get_default_expense_account(item, item_group, brand):
	return (item.get("expense_account")
		or item_group.get("expense_account")
		or brand.get("expense_account"))

def get_default_cost_center(args, item=None, item_group=None, brand=None, company=None):
	cost_center = None

	if not company and args.get("company"):
		company = args.get("company")

	if args.get('project'):
		cost_center = frappe.db.get_value("Project", args.get("project"), "cost_center", cache=True)

	if not cost_center and (item and item_group and brand):
		if args.get('customer'):
			cost_center = item.get('selling_cost_center') or item_group.get('selling_cost_center') or brand.get('selling_cost_center')
		else:
			cost_center = item.get('buying_cost_center') or item_group.get('buying_cost_center') or brand.get('buying_cost_center')

	elif not cost_center and args.get("item_code") and company:
		for method in ["get_item_defaults", "get_item_group_defaults", "get_brand_defaults"]:
			path = "erpnext.stock.get_item_details.{0}".format(method)
			data = frappe.get_attr(path)(args.get("item_code"), company)

			if data and (data.selling_cost_center or data.buying_cost_center):
				return data.selling_cost_center or data.buying_cost_center

	if not cost_center and args.get("cost_center"):
		cost_center = args.get("cost_center")

	if (company and cost_center
		and frappe.get_cached_value("Cost Center", cost_center, "company") != company):
		return None

	if not cost_center and company:
		cost_center = frappe.get_cached_value("Company",
			company, "cost_center")

	return cost_center