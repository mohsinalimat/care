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

	def validate(self):
		total_qty = total_amount = 0
		for res in self.items:
			total_qty += res.qty
			total_amount += res.amount
			split_qty = 0
			if res.code:
				data = json.loads(res.code)
				for d in data:
					if d.get('qty'):
						split_qty += float(d.get('qty'))
			else:
				frappe.throw("Please Allocate the qty in warehouse. row no <b>{0}</b>".format(res.get('idx')))

			if split_qty > res.avl_qty:
				frappe.throw("""Allocated Qty is should not be greater than the Available qty. 
								Please Allocate the qty again in row <b>{0}</b>""".format(res.idx))
			res.allocated_qty = split_qty
		self.total_qty = total_qty
		self.total_amount = total_amount


	@frappe.whitelist()
	def get_items(self):
		result = frappe.db.sql("""select distinct b.item_code, 
						i.item_name,b.stock_uom, 
						'Pack' as uom, 
						b.actual_qty 
						from `tabBin` as b 
						inner join `tabItem` as i on b.item_code = i.name
						where b.warehouse = '{0}' and b.actual_qty > 0""".format(self.hq_warehouse), as_dict=True)
		lst = []
		for res in result:
			conversion_factor = get_conversion_factor(res.item_code, res.uom).get('conversion_factor') or 1
			query = """select i.name as item_code,							
							ird.warehouse,
							ird.warehouse_reorder_level,
							ird.warehouse_reorder_qty,
							ird.optimum_level,
							b.actual_qty
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
							and i.name = '{0}'""".format(res.item_code)
			w_itm_qty = frappe.db.sql(query, as_dict=True)
			w_lst = []
			total_ord_qty_pack = 0
			for d in w_itm_qty:
				actual_qty = 0
				if d.get('actual_qty'):
					actual_qty = float(d.get('actual_qty'))
				order_qty = 0
				if self.base_on == "Reorder Quantity":
					if 0 <= actual_qty < float(d.get('warehouse_reorder_level')):
						total_qty = actual_qty + float(d.get('warehouse_reorder_qty'))
						if total_qty >= float(d.get('optimum_level')):
							order_qty = float(d.get('optimum_level')) - actual_qty
						else:
							order_qty = float(d.get('warehouse_reorder_qty'))

				if self.base_on == "Optimal Level":
					if 0 <= actual_qty < float(d.get('optimum_level')):
						total_qty = actual_qty + float(d.get('optimum_level'))
						if total_qty >= float(d.get('optimum_level')):
							order_qty = float(d.get('optimum_level')) - actual_qty
						else:
							order_qty = float(d.get('optimum_level'))
				ord_qty_pack = math.ceil(order_qty / conversion_factor)

				total_ord_qty_pack += ord_qty_pack

				w_lst.append({"warehouse": d.warehouse, "qty": ord_qty_pack, "order_qty": ord_qty_pack})
			if total_ord_qty_pack > 0:
				d = {
					"item_code": res.item_code,
					"item_name": res.item_name,
					"stock_uom": res.stock_uom,
					"uom": res.uom,
					"stock_qty": res.actual_qty,
					"qty": total_ord_qty_pack,
					"allocated_qty": total_ord_qty_pack,
					"code": w_lst
				}
				data = get_items_details(res.item_code, json.dumps(self.as_dict()),json.dumps(d))

				if data:
					d['rate'] = data.get('rate')
					d['conversion_factor'] = data.get('conversion_factor')
					d['avl_qty'] = data.get('avl_qty')
					d['stock_qty'] = data.get('stock_qty')
					d['amount'] = d['qty'] * data.get('rate')
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
				frappe.throw("Please Allocate the qty in warehouse. row no <b>{0}</b>".format(d.get('idx')))

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

		query = """select i.name as item_code,							
					ird.warehouse,
					ird.warehouse_reorder_level,
					ird.warehouse_reorder_qty,
					ird.optimum_level,
					b.actual_qty
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
					and i.name = '{0}'""".format(item_code)
		w_itm_qty = frappe.db.sql(query, as_dict=True)
		w_lst = []
		total_ord_qty_pack = 0
		for d in w_itm_qty:
			actual_qty = 0
			if d.get('actual_qty'):
				actual_qty = float(d.get('actual_qty'))
			order_qty = 0
			if doc.get('base_on') == "Reorder Quantity":
				if 0 <= actual_qty < float(d.get('warehouse_reorder_level')):
					total_qty = actual_qty + float(d.get('warehouse_reorder_qty'))
					if total_qty >= float(d.get('optimum_level')):
						order_qty = float(d.get('optimum_level')) - actual_qty
					else:
						order_qty = float(d.get('warehouse_reorder_qty'))

			if doc.get('base_on') == "Optimal Level":
				if 0 <= actual_qty < float(d.get('optimum_level')):
					total_qty = actual_qty + float(d.get('optimum_level'))
					if total_qty >= float(d.get('optimum_level')):
						order_qty = float(d.get('optimum_level')) - actual_qty
					else:
						order_qty = float(d.get('optimum_level'))

			ord_qty_pack = math.ceil(order_qty / conversion_factor)
			total_ord_qty_pack += ord_qty_pack
			w_lst.append({"warehouse": d.warehouse, "qty": ord_qty_pack, "order_qty": ord_qty_pack})

		avl_qty = float(frappe.db.sql("""select IFNULL(sum(actual_qty), 0) from `tabBin`
				where item_code = %s and warehouse = %s """, (item_code, doc.get('hq_warehouse')))[0][0] or 0)

		avl_qty_pack = math.ceil(avl_qty / conversion_factor)

		return {'rate': buying_rate,
			'conversion_factor': conversion_factor,
			'avl_qty': avl_qty_pack,
			'stock_qty': avl_qty,
			'demand': total_ord_qty_pack,
			'allocated_qty': total_ord_qty_pack,
			'code': w_lst
		}