# Copyright (c) 2021, RF and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import nowdate,getdate,cstr
from frappe.model.document import Document
import json
from frappe.utils import flt
from erpnext.controllers.taxes_and_totals import get_itemised_tax_breakup_data
from erpnext.stock.get_item_details import _get_item_tax_template
from erpnext.controllers.accounts_controller import get_taxes_and_charges


class OrderReceiving(Document):

	def validate(self):
		if self.get("__islocal"):
			self.status = 'Draft'
			self.update_total_margin()

	@frappe.whitelist()
	def update_total_margin(self):
		for res in self.items:
			margin = -100
			if res.selling_price_list_rate > 0:
				margin = (res.selling_price_list_rate - res.rate) / res.selling_price_list_rate * 100
			res.margin_percent = margin
			res.discount_after_rate = round(res.amount,2) / res.qty
		self.calculate_item_level_tax_breakup()

	def on_cancel(self):
		frappe.db.set(self, 'status', 'Cancelled')

	def on_submit(self):
		if len(self.items) <= 100 and self.warehouse:
			self.updated_price_list_and_dicsount()
			make_purchase_invoice(self)
			frappe.db.set(self, 'status', 'Submitted')
		elif len(self.items) <= 50:
			self.updated_price_list_and_dicsount()
			make_purchase_invoice(self)
			frappe.db.set(self, 'status', 'Submitted')
		else:
			self.updated_price_list_and_dicsount()
			frappe.enqueue(make_purchase_invoice, doc=self, queue='long')
			frappe.db.set(self, 'status', 'Queue')

	def calculate_item_level_tax_breakup(self):
		if self:
			itemised_tax, itemised_taxable_amount = get_itemised_tax_breakup_data(self)
			if itemised_tax:
				for res in self.items:
					total = 0
					if res.item_code in itemised_tax.keys():
						for key in itemised_tax[res.item_code].keys():
							if 'Sales Tax' in key:
								res.sales_tax = flt(itemised_tax[res.item_code][key]['tax_amount']) if \
								itemised_tax[res.item_code][key]['tax_amount'] else 0
								total += flt(res.sales_tax)
							if 'Further Tax' in key:
								res.further_tax = flt(itemised_tax[res.item_code][key]['tax_amount']) if \
								itemised_tax[res.item_code][key]['tax_amount'] else 0
								total += flt(res.further_tax)
							if 'Advance Tax' in key:
								res.advance_tax = flt(itemised_tax[res.item_code][key]['tax_amount']) if \
								itemised_tax[res.item_code][key]['tax_amount'] else 0
					res.total_include_taxes = flt(res.sales_tax + res.further_tax + res.advance_tax) + res.amount
			else:
				for res in self.items:
					res.sales_tax = res.further_tax = res.advance_tax = res.total_include_taxes = 0

	@frappe.whitelist()
	def get_item_code(self):
		i_lst = []
		select_item_list =[]
		if self.purchase_request:
			for res in self.items:
				select_item_list.append(res.item_code)

			result = frappe.db.sql("""select distinct pi.item_code from `tabPurchase Request Item` as pi
					inner join `tabPurchase Request` as p on p.name = pi.parent 
					where p.name = '{0}'""".format(self.purchase_request),as_dict=True)

			for res in result:
				if res.get('item_code') not in select_item_list:
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
							and p.applicable_for = 'Supplier' 
							and p.supplier = '{0}' 
							and pi.item_code = '{1}' 
						""".format(self.supplier, res.item_code)

					query += """ and valid_from <= '{0}' order by valid_from desc limit 1""".format(nowdate())
					result = frappe.db.sql(query)
					if result:
						p_rule = frappe.get_doc("Pricing Rule", result[0][0])
						text = ""
						# if res.discount:
						# 	text = f"""Updated Discount Amount {p_rule.discount_amount} to {res.discount} From Order Receiving"""
						# 	p_rule.rate_or_discount = 'Discount Amount'
						# 	p_rule.discount_amount = res.discount

						# if res.discount_percent:
						text = f"""Updated Discount Percentage {p_rule.discount_percentage} 
									to {res.discount_percent} From Order Receiving"""
						p_rule.rate_or_discount = 'Discount Percentage'
						p_rule.discount_percentage = res.discount_percent
						p_rule.save(ignore_permissions=True)
						p_rule.add_comment(comment_type='Info', text=text, link_doctype=p_rule.doctype, link_name=p_rule.name)
					else:
						priority = 1
						p_rule = frappe.new_doc("Pricing Rule")
						p_rule.title = 'Discount'
						p_rule.apply_on = 'Item Code'
						p_rule.price_or_product_discount = 'Price'
						p_rule.currency = self.currency
						p_rule.applicable_for = "Supplier"
						p_rule.supplier = self.supplier
						p_rule.buying = 1
						p_rule.priority = priority
						p_rule.valid_from = nowdate()
						p_rule.append("items", {'item_code': res.item_code})
						# if res.discount:
						# 	p_rule.rate_or_discount = 'Discount Amount'
						# 	p_rule.discount_amount = res.discount
						# if res.discount_percent:
						p_rule.rate_or_discount = 'Discount Percentage'
						p_rule.discount_percentage = res.discount_percent
						p_rule.save(ignore_permissions=True)
						text = "Pricing Rule created from Order Receiving"
						p_rule.add_comment(comment_type='Info', text=text, link_doctype=p_rule.doctype, link_name=p_rule.name)


def make_purchase_invoice(doc):
	material_demand = frappe.get_list("Material Demand", {'supplier': doc.supplier, 'purchase_request': doc.purchase_request},['name'])
	m_list = []
	for res in material_demand:
		m_list.append(res.name)
	if doc.items:
		if doc.warehouse:
			is_franchise = frappe.get_value("Warehouse", {'name': doc.warehouse}, "is_franchise")
			cost_center = frappe.get_value("Warehouse", {'name': doc.warehouse}, "cost_center")
			pi = frappe.new_doc("Purchase Receipt")
			pi.supplier = doc.supplier
			pi.posting_date = nowdate()
			pi.due_date = nowdate()
			pi.company = doc.company
			pi.taxes_and_charges = doc.taxes_and_charges
			pi.order_receiving = doc.name
			pi.update_stock = 1 if not is_franchise else 0
			pi.set_warehouse = doc.warehouse
			pi.cost_center = cost_center
			pi.ignore_pricing_rule = 1
			for d in doc.items:
				md_item = frappe.get_value("Material Demand Item", {'item_code': d.get('item_code'), 'parent': ['in', m_list], "warehouse": doc.warehouse}, "name")
				if md_item:
					md_doc = frappe.get_doc("Material Demand Item", md_item)
					pi.append("items", {
						"item_code": d.get('item_code'),
						"warehouse": md_doc.warehouse,
						"qty": d.get('qty'),
						"received_qty": d.get('qty'),
						"rate": d.get('discount_after_rate'),
						"expense_account": md_doc.expense_account,
						"cost_center": md_doc.cost_center,
						"uom": md_doc.uom,
						"item_tax_template": d.get('item_tax_template'),
						"item_tax_rate": d.get('item_tax_rate'),
						"stock_Uom": md_doc.stock_uom,
						"material_demand": md_doc.parent,
						"material_demand_item": md_doc.name,
						"order_receiving_item": d.name,
						"margin_type": "Percentage" if d.get("discount_percent") else None,
						"discount_percentage": d.get("discount_percent"),
					})

				else:
					if not doc.ignore_un_order_item:
						frappe.throw(_("Item <b>{0}</b> not found in Material Demand").format(d.get('item_code')))
			if pi.get('items'):
				taxes = get_taxes_and_charges('Purchase Taxes and Charges Template', doc.taxes_and_charges)
				for tax in taxes:
					pi.append('taxes',tax)
				pi.set_missing_values()
				for res in pi.items:
					if res.order_receiving_item:
						if not frappe.get_value("Order Receiving Item", res.order_receiving_item, 'item_tax_template'):
							res.item_tax_template = None
							res.item_tax_rate = '{}'
				pi.insert(ignore_permissions=True)

		else:
			item_details = {}
			for d in doc.items:
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
										s = {
											"item_code": d.get('item_code'),
											"warehouse": md_doc.warehouse,
											"qty": res.get('qty'),
											"received_qty": res.get('qty'),
											"rate": d.get('discount_after_rate'),
											"expense_account": md_doc.expense_account,
											"cost_center": md_doc.cost_center,
											"uom": md_doc.uom,
											"stock_Uom": md_doc.stock_uom,
											"material_demand": md_doc.parent,
											"material_demand_item": md_doc.name,
											"order_receiving_item": d.name,
											"item_tax_template": d.get('item_tax_template'),
											"item_tax_rate": d.get('item_tax_rate'),
											"margin_type": "Percentage" if d.get("discount_percent") else None,
											"discount_percentage": d.get("discount_percent"),
										}
										key = (md_doc.warehouse)
										item_details.setdefault(key, {"details": []})
										fifo_queue = item_details[key]["details"]
										fifo_queue.append(s)
							else:
								if not doc.ignore_un_order_item:
									frappe.throw(_("Item <b>{0}</b> not found in Material Demand").format(d.get('item_code')))
				else:
					md_item = frappe.get_list("Material Demand Item", {'item_code': d.get('item_code'), 'parent': ['in', m_list]}, ['name'])
					received_qty = d.get('qty')
					if md_item:
						for p_tm in md_item:
							if received_qty > 0:
								md_doc = frappe.get_doc("Material Demand Item", p_tm.name)
								if md_doc:
									s = {
										"item_code": d.get('item_code'),
										"warehouse": md_doc.warehouse,
										"qty": md_doc.qty if md_doc.qty <= received_qty else received_qty,
										"received_qty": md_doc.qty if md_doc.qty <= received_qty else received_qty,
										"rate": d.get('discount_after_rate'),
										"expense_account": md_doc.expense_account,
										"cost_center": md_doc.cost_center,
										"uom": md_doc.uom,
										"stock_Uom": md_doc.stock_uom,
										"material_demand": md_doc.parent,
										"material_demand_item": md_doc.name,
										"order_receiving_item": d.name,
										"item_tax_template": d.get('item_tax_template'),
										"item_tax_rate": d.get('item_tax_rate'),
										"margin_type": "Percentage" if d.get("discount_percent") else None,
										"discount_percentage": d.get("discount_percent"),
									}
									received_qty -= md_doc.qty

									key = (md_doc.warehouse)
									item_details.setdefault(key, {"details": []})
									fifo_queue = item_details[key]["details"]
									fifo_queue.append(s)
						if received_qty > 0:
							s = {
								"item_code": d.get('item_code'),
								"warehouse": doc.c_b_warehouse,
								"qty": received_qty,
								"received_qty": received_qty,
								"rate": d.get('discount_after_rate'),
								"uom": d.get('uom'),
								"stock_Uom": d.get('stock_uom'),
								"item_tax_template": d.get('item_tax_template'),
								"item_tax_rate": d.get('item_tax_rate'),
								"order_receiving_item": d.name,
								"margin_type": "Percentage" if d.get("discount_percent") else None,
								"discount_percentage": d.get("discount_percent"),
							}
							key = (doc.c_b_warehouse)
							item_details.setdefault(key, {"details": []})
							fifo_queue = item_details[key]["details"]
							fifo_queue.append(s)

					else:
						if not doc.ignore_un_order_item:
							frappe.throw(_("Item <b>{0}</b> not found in Material Demand").format(d.get('item_code')))
			if item_details:
				if item_details:
					for key in item_details.keys():
						try:
							is_franchise = frappe.get_value("Warehouse", {'name': key}, "is_franchise")
							cost_center = frappe.get_value("Warehouse", {'name': key}, "cost_center")
							pi = frappe.new_doc("Purchase Receipt")
							pi.supplier = doc.supplier
							pi.posting_date = nowdate()
							pi.due_date = nowdate()
							pi.company = doc.company
							pi.taxes_and_charges = doc.taxes_and_charges
							pi.order_receiving = doc.name
							pi.purchase_request = doc.purchase_request
							pi.update_stock = 1 if not is_franchise else 0
							pi.set_warehouse = key
							pi.cost_center = cost_center
							pi.ignore_pricing_rule = 1
							for d in item_details[key]['details']:
								pi.append("items", d)
							if pi.get('items'):
								taxes = get_taxes_and_charges('Purchase Taxes and Charges Template', doc.taxes_and_charges)
								for tax in taxes:
									pi.append('taxes', tax)
								pi.set_missing_values()
								for res in pi.items:
									if res.order_receiving_item:
										if not frappe.get_value("Order Receiving Item", res.order_receiving_item,
																'item_tax_template'):
											res.item_tax_template = None
											res.item_tax_rate = '{}'
								pi.insert(ignore_permissions=True)
						except:
							continue
		frappe.msgprint(_("Purchase Receipt Created"), alert=1)

	frappe.db.set(doc, 'status', 'Submitted')

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

@frappe.whitelist()
def get_warehouse(purchase_request,item):
	if purchase_request and item:
		result = frappe.db.sql("""select w.name as warehouse, 
							IFNULL(sum(p.pack_order_qty), 0) as order_qty,
							IFNULL(sum(p.pack_order_qty), 0) as qty
							from `tabWarehouse` as w 
							left join `tabPurchase Request Item` as p on w.name = p.warehouse and p.parent ='{0}' and p.item_code ='{1}'
							where w.is_group = 0 and w.auto_select_in_purchase_request = 1 
							group by w.name""".format(purchase_request,item), as_dict=True)
		return result
	return []


@frappe.whitelist()
def get_item_tax_template(item, args, out= None):
	"""
	args = {
	        "tax_category": None
	        "item_tax_template": None
	}
	"""

	item = frappe.get_doc("Item", item)
	item_tax_template = None
	args = json.loads(args)
	if item.taxes:
		item_tax_template = _get_item_tax_template(args, item.taxes, out)
		return item_tax_template

	if not item_tax_template:
		item_group = item.item_group
		while item_group and not item_tax_template:
			item_group_doc = frappe.get_cached_doc("Item Group", item_group)
			item_tax_template = _get_item_tax_template(args, item_group_doc.taxes, out)
			return item_tax_template
