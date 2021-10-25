# Copyright (c) 2021, RF and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from care.care.doctype.purchase_request.purchase_request import get_default_expense_account,get_item_defaults,get_item_group_defaults,get_brand_defaults,get_default_cost_center
from erpnext.stock.get_item_details import get_conversion_factor

class MaterialDemand(Document):
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

