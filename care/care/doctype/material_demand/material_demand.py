# Copyright (c) 2021, RF and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from care.care.doctype.purchase_request.purchase_request import get_default_expense_account,get_item_defaults,get_item_group_defaults,get_brand_defaults,get_default_cost_center
from erpnext.stock.get_item_details import get_conversion_factor

class MaterialDemand(Document):
	def before_submit(self):
		self.status = "Pending"
		total_qty = 0
		for res in self.items:
			total_qty += (res.qty)
		self.total_qty = total_qty

	def on_cancel(self):
		# doctypes = get_linked_doctypes(self.doctype)
		self.status = "Cancelled"
		self.db_update()

	def before_save(self):
		for d in self.items:
			item_defaults = get_item_defaults(d.item_code, self.company)
			item_group_defaults = get_item_group_defaults(d.item_code, self.company)
			brand_defaults = get_brand_defaults(d.item_code, self.company)
			if not d.expense_account:
				expense_account = get_default_expense_account(item_defaults, item_group_defaults, brand_defaults)
				d.expense_account = expense_account
			if not d.cost_center:
				cost_center = get_default_cost_center(self, item_defaults, item_group_defaults, brand_defaults)
				d.cost_center = cost_center
			conversion_factor = 1
			conversion = get_conversion_factor(d.item_code, d.uom)
			if conversion:
				conversion_factor = conversion['conversion_factor']
			d.stock_qty = d.qty * conversion_factor
			d.amount = d.qty * d.rate

	@frappe.whitelist()
	def make_purchase_order(self):
		po = frappe.new_doc("Purchase Order")
		po.supplier = self.supplier
		po.company = self.company
		po.transaction_date = self.transaction_date
		po.schedule_date = self.schedule_date
		po.set_warehouse = self.warehouse
		for line in self.items:
			remain_qty = line.qty - line.ordered_qty
			if remain_qty > 0:
				item = frappe.get_doc("Item", line.item_code)
				po.append("items", {
					"item_code": line.item_code,
					"description": item.description,
					"brand": line.brand,
					"warehouse": line.warehouse,
					"qty": line.qty - line.ordered_qty,
					"rate": line.rate,
					"stock_uom": line.stock_uom,
					"uom": line.uom,
					"conversion_factor": line.conversion_factor,
					"allow_zero_valuation_rate": 0,
					"material_demand": self.name,
					"material_demand_item": line.name
				})
		po.set_missing_values()
		# po.insert(ignore_permissions=True)
		return po.as_dict()

