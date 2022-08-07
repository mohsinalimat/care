# Copyright (c) 2022, RF and contributors
# For license information, please see license.txt

import frappe
import math
import json
from frappe.utils import nowdate
from erpnext.stock.get_item_details import get_conversion_factor
from care.hook_events.purchase_invoice import get_price_list_rate_for

def execute(filters=None):
	if not filters.get('warehouse'):
		frappe.throw("Select Warehouse")
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_columns():
	column = [
		{
			"fieldname": "item_code",
			"fieldtype": "Link",
			"label": "Item",
			"options": "Item",
			"width": 250
		},
		{
			"fieldname": "item_name",
			"fieldtype": "Data",
			"label": "Item Name",
			"width": 200,
			"hidden": 1
		},
		{
			"fieldname": "brand",
			"fieldtype": "Data",
			"label": "Brand",
			"width": 180,
		},
		{
			"fieldname": "uom",
			"fieldtype": "Link",
			"label": "UOM",
			"options": "UOM",
			"width": 120
		},
		{
			"fieldname": "qty",
			"fieldtype": "Float",
			"label": "Qty",
			"width": 130
		},
		{
			"fieldname": "rate",
			"fieldtype": "Currency",
			"label": "Rate",
			"width": 130
		},
		{
			"fieldname": "amount",
			"fieldtype": "Currency",
			"label": "Amount",
			"width": 130
		}
	]
	return column

def get_data(filters):

	data = []
	query = """select i.name as item_code,
			i.item_name,
			i.brand,
			idf.default_supplier,
			ird.warehouse_reorder_level,
			ird.warehouse_reorder_qty,
			ird.optimum_level,
			b.actual_qty,
			i.stock_uom
			from `tabItem` i 
			inner join `tabItem Default` idf on idf.parent = i.name
			inner  join `tabItem Reorder` ird on ird.parent = i.name
			left join `tabBin` b on b.item_code = i.name and b.warehouse = ird.warehouse
			where 
			idf.default_supplier is not null and 
			ird.warehouse is not null
			and i.is_stock_item = 1 
			and i.has_variants = 0
			and i.disabled = 0
			and ird.warehouse_reorder_level > 0 
			and ird.warehouse_reorder_qty > 0 
			and ird.optimum_level > 0
			and (b.actual_qty < ird.warehouse_reorder_level or b.actual_qty is null)
			and ird.warehouse = '{0}' """.format(filters.get('warehouse'))
	if filters.get('supplier'):
		query += """ and idf.default_supplier = '{0}'""".format(filters.get('supplier'))
	query += " order by i.name"
	item_details = frappe.db.sql(query, as_dict=True)

	for d in item_details:
		conversion_factor = 1
		conversion = get_conversion_factor(d.item_code, 'Pack')
		if conversion:
			conversion_factor = conversion['conversion_factor']

		actual_qty = 0
		if d.get('actual_qty'):
			actual_qty = float(d.get('actual_qty'))

		order_qty = 0
		if filters.get('base_on') == "Reorder Quantity":
			if 0 <= actual_qty < float(d.get('warehouse_reorder_level')):
				total_qty = actual_qty + float(d.get('warehouse_reorder_qty'))
				if total_qty >= float(d.get('optimum_level')):
					order_qty = float(d.get('optimum_level')) - actual_qty
				else:
					order_qty = float(d.get('warehouse_reorder_qty'))

		if filters.get('base_on') == "Optimal Level":
			if 0 <= actual_qty < float(d.get('optimum_level')):
				total_qty = actual_qty + float(d.get('optimum_level'))
				if total_qty >= float(d.get('optimum_level')):
					order_qty = float(d.get('optimum_level')) - actual_qty
				else:
					order_qty = float(d.get('optimum_level'))

		j_d = json.dumps({
			"item_code": d.get('item_code'),
			"price_list": frappe.defaults.get_defaults().buying_price_list,
			"currency": frappe.defaults.get_defaults().currency,
			"price_list_currency": frappe.defaults.get_defaults().currency,
			"supplier": d.get('default_supplier'),
			"uom": 'Pack',
			"stock_uom": d.get('stock_uom'),
			"qty": 1,
			"transaction_date": nowdate(),
			"doctype": None,
			"name": None,
			"conversion_factor": conversion_factor
		})
		rate = get_price_list_rate_for(d.get('item_code'), j_d)
		pack_order_qty = math.floor(order_qty / conversion_factor)

		d_dict = {
			"item_code": d.get('item_code'),
			"item_name": d.get('item_name'),
			"brand": d.get('brand'),
			"uom": "Pack",
			"qty": pack_order_qty,
			"rate": rate,
			"amount": pack_order_qty * rate
		}
		data.append(d_dict)

	return data
