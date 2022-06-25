# Copyright (c) 2022, RF and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import nowdate, getdate, cstr
from frappe.model.document import Document
import json
import math
from erpnext.stock.get_item_details import get_conversion_factor
from care.hook_events.purchase_invoice import get_price_list_rate_for

class HQTransfer(Document):
	@frappe.whitelist()
	def get_item_code(self):
		i_lst = []
		select_item_list = []
		if self.purchase_request:
			if self.get('items'):
				for res in self.get('items'):
					select_item_list.append(res.item_code)

			result = frappe.db.sql("""select distinct pi.item_code from `tabPurchase Request Item` as pi
				inner join `tabPurchase Request` as p on p.name = pi.parent 
				where p.name = '{0}'""".format(self.purchase_request), as_dict=True)

			for res in result:
				if res.get('item_code') not in select_item_list:
					i_lst.append(res.get('item_code'))
		return i_lst

	def validate(self):
		total_qty = total_amount = 0
		for res in self.items:
			total_qty += res.qty
			total_amount += res.amount
			if res.qty > res.avl_qty and not res.code:
				frappe.throw("""Demand is greater than the Available qty in row <b>{0}</b>. 
						<span style='color:red'>please split the Qty.</span>""".format(res.idx))

		self.total_qty = total_qty
		self.total_amount = total_amount

	def set_missing_value(self):
		company = self.get('company')
		buying_price_list = frappe.defaults.get_defaults().buying_price_list
		currency = frappe.defaults.get_defaults().currency
		for item in self.items:
			conversion_factor = get_conversion_factor(item.get('item_code'), item.get('uom')).get('conversion_factor') or 1
			args = {
				'item_code': item.get('item_code'),
				'supplier': item.get('supplier'),
				'currency': company,
				'price_list': buying_price_list,
				'price_list_currency': currency,
				'company': company,
				'transaction_date': item.get('posting_date'),
				'doctype': item.get('doctype'),
				'name': item.get('name'),
				'qty': item.get('qty') or 1,
				'child_docname': item.get('name'),
				'uom': item.get('uom'),
				'stock_uom': item.get('stock_uom'),
				'conversion_factor': conversion_factor
			}
			buying_rate = get_price_list_rate_for(item.get('item_code'), json.dumps(args)) or 0

			demand = float(frappe.db.sql("""select IFNULL(sum(pack_order_qty), 0)
												from `tabPurchase Request Item`
												where parent ='{0}' and item_code ='{1}'
												""".format(self.get('purchase_request'), item.get('item_code')))[0][0] or 0)

			avl_qty = float(frappe.db.sql("""select IFNULL(actual_qty - reserved_qty, 0) from `tabBin`
							where item_code = %s and warehouse = %s
							limit 1""", (item.get('item_code'), self.get('hq_warehouse')))[0][0] or 0)

			avl_qty_pack = math.ceil(avl_qty / conversion_factor)

			item.rate = buying_rate
			item.conversion_factor = conversion_factor
			item.avl_qty = avl_qty_pack
			item.stock_qty = avl_qty
			item.qty = demand
			item.amount = avl_qty_pack * buying_rate

	@frappe.whitelist()
	def get_items(self):
		result = frappe.db.sql("""select distinct pi.item_code,pi.item_name,pi.stock_uom,'Pack' as uom, b.actual_qty from `tabPurchase Request Item` as pi
						inner join `tabPurchase Request` as p on p.name = pi.parent
						inner join `tabBin` as b on  b.item_code = pi.item_code and b.warehouse = '{0}' 
						where p.name = '{1}' and b.actual_qty > 0""".format(self.hq_warehouse, self.purchase_request), as_dict=True)
		lst = []
		for res in result:
			d = {
				"item_code": res.item_code,
				"item_name": res.item_name,
				"stock_uom": res.stock_uom,
				"uom": res.uom,
				"stock_qty": res.actual_qty
			}
			data = get_items_details(res.item_code, json.dumps(self.as_dict()),json.dumps(d))
			if data:
				d['rate'] = data.get('rate')
				d['conversion_factor'] = data.get('conversion_factor')
				d['avl_qty'] = data.get('avl_qty')
				d['stock_qty'] = data.get('stock_qty')
				d['qty'] = data.get('demand')
				d['amount'] = data.get('demand') * data.get('rate')
			lst.append(d)
		if lst:
			return lst
		else:
			frappe.throw(_("No Item stock found in <b>{0}</b>".format(self.hq_warehouse)))

	def on_submit(self):
		make_stock_entry(self)

def make_stock_entry(doc):
	if doc.items:
		item_details = {}
		for d in doc.items:
			if d.code:
				data = json.loads(d.code)
				for res in data:
					if res.get('qty') > 0:
						s = {
							"item_code": d.get('item_code'),
							"from_warehouse": doc.hq_warehouse,
							"to_warehouse": res.get('warehouse'),
							"qty": res.get('qty'),
							"rate": d.get('rate'),
							"uom": d.get('uom'),
							"stock_Uom": d.get('stock_uom'),
							"margin_type": "Percentage" if d.get("discount_percent") else None,
							"discount_percentage": d.get("discount_percent"),
						}
						key = (res.get('warehouse'))
						item_details.setdefault(key, {"details": []})
						fifo_queue = item_details[key]["details"]
						fifo_queue.append(s)
			else:
				pr_item = frappe.get_list("Purchase Request Item",
										{'item_code': d.get('item_code'),
										'parent': ['=', doc.purchase_request]}, ['name'])

				received_qty = d.get('qty')
				if pr_item:
					for p_tm in pr_item:
						if received_qty > 0:
							pr_doc = frappe.get_doc("Purchase Request Item", p_tm.name)
							if pr_doc:
								qty = pr_doc.pack_order_qty if pr_doc.pack_order_qty <= received_qty else received_qty
								s = {
									"item_code": d.get('item_code'),
									"from_warehouse": doc.hq_warehouse,
									"to_warehouse": pr_doc.warehouse,
									"qty": qty,
									"rate": d.get('rate'),
									"uom": d.get('uom'),
									"stock_Uom": d.get('stock_uom'),
									"margin_type": "Percentage" if d.get("discount_percent") else None,
									"discount_percentage": d.get("discount_percent"),
								}
								received_qty -= pr_doc.pack_order_qty
								key = (pr_doc.warehouse)
								item_details.setdefault(key, {"details": []})
								fifo_queue = item_details[key]["details"]
								fifo_queue.append(s)
		if item_details:
			if item_details:
				for key in item_details.keys():
					try:
						pi = frappe.new_doc("Stock Entry")
						pi.purpose = 'Material Transfer'
						pi.stock_entry_type = 'Material Transfer'
						pi.posting_date = doc.posting_date
						pi.company = doc.company
						pi.hq_transfer = doc.name
						pi.from_warehouse = doc.hq_warehouse
						pi.to_warehouse = key
						pi.ignore_pricing_rule = 1
						for d in item_details[key]['details']:
							pi.append("items", d)
						if pi.get('items'):
							pi.set_missing_values()
							pi.insert(ignore_permissions=True)
							pi.submit()
					except Exception as e:
						print("---------error: ", e)
						continue

	frappe.msgprint(_("Stock Entry Created"), alert=1)

@frappe.whitelist()
def get_warehouse(purchase_request, item):
	if purchase_request and item:
		result = frappe.db.sql("""select warehouse, 
			IFNULL(sum(pack_order_qty), 0) as order_qty,
			IFNULL(sum(pack_order_qty), 0) as qty 
			from `tabPurchase Request Item`
			where parent ='{0}' and item_code ='{1}'
			group by warehouse""".format(purchase_request, item), as_dict=True)
		return result
	return []


@frappe.whitelist()
def get_items_details(item_code, doc, item):
	if item_code:
		doc = json.loads(doc)
		item = json.loads(item)
		company = doc.get('company')
		buying_price_list = frappe.defaults.get_defaults().buying_price_list
		currency = frappe.defaults.get_defaults().currency
		conversion_factor = get_conversion_factor(item_code, item.get('uom')).get('conversion_factor') or 1
		args = {
			'item_code': item.get('item_code'),
			'supplier': doc.get('supplier'),
			'currency': company,
			'price_list':buying_price_list,
			'price_list_currency': currency,
			'company': company,
			'transaction_date': doc.get('posting_date'),
			'doctype': doc.get('doctype'),
			'name': doc.get('name'),
			'qty': item.get('qty') or 1,
			'child_docname': item.get('name'),
			'uom': item.get('uom'),
			'stock_uom': item.get('stock_uom'),
			'conversion_factor': conversion_factor
		}
		buying_rate = get_price_list_rate_for(item_code, json.dumps(args)) or 0

		demand = float(frappe.db.sql("""select sum(pack_order_qty)
									from `tabPurchase Request Item`
									where parent ='{0}' and item_code ='{1}'
									""".format(doc.get('purchase_request'), item_code))[0][0] or 0)

		avl_qty = float(frappe.db.sql("""select IFNULL(actual_qty, 0) from `tabBin`
				where item_code = %s and warehouse = %s
				limit 1""", (item_code, doc.get('hq_warehouse')))[0][0] or 0)

		avl_qty_pack = math.ceil(avl_qty / conversion_factor)

		return {'rate': buying_rate,
			'conversion_factor': conversion_factor,
			'avl_qty': avl_qty_pack,
			'stock_qty': avl_qty,
			'demand': demand
		}