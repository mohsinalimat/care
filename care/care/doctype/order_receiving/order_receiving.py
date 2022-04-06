# Copyright (c) 2021, RF and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import nowdate
from frappe.model.document import Document
import json

class OrderReceiving(Document):

	def validate(self):
		for res in self.items:
			margin = -100
			if res.selling_price_list_rate > 0:
				margin = (res.selling_price_list_rate - res.rate) / res.selling_price_list_rate * 100
			res.margin_percent = margin

	def on_submit(self):
		self.make_purchase_invoice()
		self.updated_price_list_and_dicsount()

	@frappe.whitelist()
	def get_warehouse(self):
		wr = frappe.get_list("Warehouse", filters={'is_group': 0, 'auto_select_in_purchase_request': 1}, fields='*', order_by='name')
		lst = []
		for res in wr:
			lst.append({"warehouse": res.name, "qty": 0})
		return lst

	@frappe.whitelist()
	def get_item_code(self):
		i_lst = []
		if self.purchase_request:
			result = frappe.db.sql("""select distinct pi.item_code from `tabPurchase Request Item` as pi
					inner join `tabPurchase Request` as p on p.name = pi.parent 
					where p.name = '{0}'""".format(self.purchase_request),as_dict=True)

			for res in result:
				i_lst.append(res.get('item_code'))
		return i_lst

	def updated_price_list_and_dicsount(self):
		if self.update_buying_price or self.update_selling_price:
			for res in self.items:
				if self.update_buying_price and res.rate != res.base_buying_price_list_rate:
					buying_price_list = frappe.get_value("Item Price", {'item_code': res.item_code,
																	'price_list': self.buying_price_list,
																	'buying': 1}, ['name'])
					if buying_price_list:
						item_price = frappe.get_doc("Item Price", buying_price_list)
						item_price.price_list_rate = res.rate / res.conversion_factor
						item_price.save(ignore_permissions=True)
				if self.update_selling_price and res.selling_price_list_rate != res.base_selling_price_list_rate:
					selling_price_list = frappe.get_value("Item Price", {'item_code': res.item_code,
																		'price_list': self.base_selling_price_list,
																		'selling': 1}, ['name'])
					if selling_price_list:
						item_price = frappe.get_doc("Item Price", selling_price_list)
						item_price.price_list_rate = res.selling_price_list_rate / res.conversion_factor
						item_price.save(ignore_permissions=True)
				if self.update_discount and (res.discount or res.discount_percent):
					query = """select p.name from `tabPricing Rule` as p 
						inner join `tabPricing Rule Item Code` as pi on pi.parent = p.name 
						where p.apply_on = 'Item Code' 
							and p.disable = 0 
							and p.price_or_product_discount = 'Price' 
						"""
					if res.discount:
						query += """ and p.rate_or_discount = 'Discount Amount' 
									and p.discount_amount = {0}""".format(res.discount)
					if res.discount_percent:
						query += """ and p.rate_or_discount = 'Discount Percentage' 
								and p.discount_percentage = {0}""".format(res.discount_percent)

					query += """ and valid_from <= '{0}' order by valid_from desc limit 1""".format(nowdate())
					result = frappe.db.sql(query)
					if len(result) == 0:
						p_rule = frappe.new_doc("Pricing Rule")
						p_rule.title = 'Discount'
						p_rule.apply_on = 'Item Code'
						p_rule.price_or_product_discount = 'Price'
						p_rule.currency = self.currency
						p_rule.company = self.company
						p_rule.buying = 1
						p_rule.valid_from = nowdate()
						p_rule.append("items", {'item_code': res.item_code})
						if res.discount:
							p_rule.rate_or_discount = 'Discount Amount'
							p_rule.discount_amount = res.discount
						if res.discount_percent:
							p_rule.rate_or_discount = 'Discount Percentage'
							p_rule.discount_percentage = res.discount_percent
						p_rule.save(ignore_permissions=True)


	def make_purchase_invoice(self):
		material_demand = frappe.get_list("Material Demand", {'supplier': self.supplier, 'purchase_request': self.purchase_request},['name'])
		m_list = []
		for res in material_demand:
			m_list.append(res.name)
		if self.items:
			if self.warehouse:
				is_franchise = frappe.get_value("Warehouse", {'name': self.warehouse}, "is_franchise")
				cost_center = frappe.get_value("Warehouse", {'name': self.warehouse}, "cost_center")
				pi = frappe.new_doc("Purchase Receipt")
				pi.supplier = self.supplier
				pi.posting_date = nowdate()
				pi.due_date = nowdate()
				pi.company = self.company
				pi.order_receiving = self.name
				pi.update_stock = 1 if not is_franchise else 0
				pi.set_warehouse = self.warehouse
				pi.cost_center = cost_center
				for d in self.items:
					md_item = frappe.get_value("Material Demand Item", {'item_code': d.get('item_code'), 'parent': ['in', m_list], "warehouse": self.warehouse}, "name")
					if md_item:
						md_doc = frappe.get_doc("Material Demand Item", md_item)
						pi.append("items", {
							"item_code": d.get('item_code'),
							"warehouse": md_doc.warehouse,
							"qty": d.get('qty'),
							"received_qty": d.get('qty'),
							"rate": d.get('rate'),
							"expense_account": md_doc.expense_account,
							"cost_center": md_doc.cost_center,
							"uom": md_doc.uom,
							"stock_Uom": md_doc.stock_uom,
							"material_demand": md_doc.parent,
							"material_demand_item": md_doc.name,
						})

					else:
						if not self.ignore_un_order_item:
							frappe.throw(_("Item <b>{0}</b> not found in Material Demand").format(d.get('item_code')))
				if pi.get('items'):
					pi.set_missing_values()
					pi.insert(ignore_permissions=True)

			else:
				item_details = {}
				for d in self.items:
					if d.code:
						data = json.loads(d.code)
						for res in data:
							if res.get('qty') > 0:
								md_item = frappe.get_list("Material Demand Item", {'item_code': d.get('item_code'),
																				'warehouse': res.get('warehouse'),
																				'parent': ['in', m_list]}, ['name'])
								if md_item:
									for p_tm in md_item:
										md_doc = frappe.get_doc("Material Demand Item", p_tm.name)
										if md_doc:
											margin_type = None
											if d.get("discount_percent"):
												margin_type = "Percentage"
											if d.get("discount"):
												margin_type = "Amount"
											d = {
												"item_code": d.get('item_code'),
												"warehouse": md_doc.warehouse,
												"qty": res.get('qty'),
												"received_qty": res.get('qty'),
												"rate": d.get('rate'),
												"expense_account": md_doc.expense_account,
												"cost_center": md_doc.cost_center,
												"uom": md_doc.uom,
												"stock_Uom": md_doc.stock_uom,
												"material_demand": md_doc.parent,
												"material_demand_item": md_doc.name,
												"margin_type": margin_type,
												"discount_percentage": d.get("discount_percent"),
												"discount_amount": d.get("discount"),
											}
											key = (md_doc.warehouse)
											item_details.setdefault(key, {"details": []})
											fifo_queue = item_details[key]["details"]
											fifo_queue.append(d)
								else:
									if not self.ignore_un_order_item:
										frappe.throw(_("Item <b>{0}</b> not found in Material Demand").format(d.get('item_code')))
					else:
						md_item = frappe.get_list("Material Demand Item", {'item_code': d.get('item_code'), 'parent': ['in', m_list]}, ['name'])
						received_qty = d.get('qty')
						if md_item:
							for p_tm in md_item:
								if received_qty > 0:
									md_doc = frappe.get_doc("Material Demand Item", p_tm.name)
									if md_doc:
										margin_type = None
										if d.get("discount_percent"):
											margin_type = "Percentage"
										if d.get("discount"):
											margin_type = "Amount"
										d = {
											"item_code": d.get('item_code'),
											"warehouse": md_doc.warehouse,
											"qty": md_doc.qty if md_doc.qty <= received_qty else received_qty,
											"received_qty": md_doc.qty if md_doc.qty <= received_qty else received_qty,
											"rate": d.get('rate'),
											"expense_account": md_doc.expense_account,
											"cost_center": md_doc.cost_center,
											"uom": md_doc.uom,
											"stock_Uom": md_doc.stock_uom,
											"material_demand": md_doc.parent,
											"material_demand_item": md_doc.name,
											"margin_type": margin_type,
											"discount_percentage": d.get("discount_percent"),
											"discount_amount": d.get("discount"),
										}
										received_qty -= md_doc.qty

										key = (md_doc.warehouse)
										item_details.setdefault(key, {"details": []})
										fifo_queue = item_details[key]["details"]
										fifo_queue.append(d)
						else:
							if not self.ignore_un_order_item:
								frappe.throw(_("Item <b>{0}</b> not found in Material Demand").format(d.get('item_code')))
				if item_details:
					if item_details:
						for key in item_details.keys():
							try:
								is_franchise = frappe.get_value("Warehouse", {'name': key}, "is_franchise")
								cost_center = frappe.get_value("Warehouse", {'name': key}, "cost_center")
								pi = frappe.new_doc("Purchase Receipt")
								pi.supplier = self.supplier
								pi.posting_date = nowdate()
								pi.due_date = nowdate()
								pi.company = self.company
								pi.order_receiving = self.name
								pi.purchase_request = self.purchase_request
								pi.update_stock = 1 if not is_franchise else 0
								pi.set_warehouse = key
								pi.cost_center = cost_center
								for d in item_details[key]['details']:
									pi.append("items", d)
								if pi.get('items'):
									pi.set_missing_values()
									pi.insert(ignore_permissions=True)
							except:
								continue
			frappe.msgprint(_("Purchase Receipt Created"), alert=1)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_item_code(doctype, txt, searchfield, start, page_len, filters):
	if filters.get('purchase_request'):
		result = frappe.db.sql("""select distinct pi.item_code, pi.item_name from `tabPurchase Request Item` as pi
				inner join `tabPurchase Request` as p on p.name = pi.parent 
				where p.name = '{0}'""".format(filters.get('purchase_request')))
		return result
	else:
		return (" ", )


@frappe.whitelist()
def get_item_qty(purchase_request, item, supplier, warehouse=None):
	if purchase_request and supplier and item:
		if warehouse:
			qty = float(frappe.db.sql("""select sum(pack_order_qty) from `tabPurchase Request Item` 
							where item_code = '{0}' 
							and parent = '{1}' 
							and supplier = '{2}' 
							and warehouse = '{3}'""".format(item, purchase_request, supplier, warehouse))[0][0] or 0)
			return qty
		else:
			qty = float(frappe.db.sql("""select sum(pack_order_qty) from `tabPurchase Request Item` 
							where item_code = '{0}' 
							and parent = '{1}' 
							and supplier = '{2}'""".format(item, purchase_request, supplier))[0][0] or 0)
			return qty
	else:
		return 0