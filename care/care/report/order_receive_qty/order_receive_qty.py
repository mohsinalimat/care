# Copyright (c) 2022, RF and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	if not filters.get('order_receiving'):
		frappe.msgprint(_("Please select Order Receiving"))
		return [], []

	columns, data = get_columns(), get_datas(filters)
	return columns, data

def get_columns():
	columns = [
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
			"fieldname": "uom",
			"fieldtype": "Link",
			"label": "UOM",
			"options": "UOM",
			"width": 100
		},
		{
			"fieldname": "purchase_receipt",
			"fieldtype": "Link",
			"label": "Purchase Receipt",
			"options": "Purchase Receipt",
			"width": 200
		},
		{
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"label": "Warehouse",
			"options": "Warehouse",
			"width": 200
		},
		{
			"fieldname": "order_qty",
			"fieldtype": "Data",
			"label": "Order Qty",
			"width": 120
		},
		{
			"fieldname": "receive_qty",
			"fieldtype": "Data",
			"label": "Receive Qty",
			"width": 120
		},
		{
			"fieldname": "status",
			"fieldtype": "Data",
			"label": "PR Status",
			"width": 150
		},
	]
	return columns

def get_datas(filters):
	query = """select OI.item_code, OI.item_name, OI.uom,
			OI.qty as order_qty, PRI.qty as receive_qty, 
			PRI.warehouse, PR.name as purchase_receipt, 
			PR.status, 0 as indent 
			from `tabOrder Receiving` as O
			inner join `tabOrder Receiving Item` as OI on O.name = OI.parent
			inner join `tabPurchase Receipt` as PR on PR.order_receiving = O.name
			inner join `tabPurchase Receipt Item` as PRI on PRI.parent = PR.name and PRI.item_code = OI.item_code 
			where 
			O.company = '{0}' and O.name = '{1}'""".format(filters.get('company'), filters.get('order_receiving'))

	if filters.get('item'):
		query += """ and OI.item_code ='{0}'""".format(filters.get('item'))

	if filters.get('warehouse'):
		query += """ and PRI.warehouse ='{0}'""".format(filters.get('warehouse'))

	query += " order by OI.item_code, OI.item_name"

	result = frappe.db.sql(query, as_dict=True)

	item_details = {}
	for res in result:
		key = str(res.item_code) + ":" + str(res.item_name) + ":" + str(res.uom)
		item_details.setdefault(key, [])
		item_details[key].append(res)

	data = []
	for key in item_details.keys():
		total_or_qty = total_rq_qty = 0
		lst = []
		for res in item_details[key]:
			total_or_qty = res.order_qty
			total_rq_qty += res.receive_qty
			res['order_qty'] = None
			res['indent'] = 1
			lst.append(res)
		s_key = key.split(":")
		data.append({
			'item_code': "<b>" + str(s_key[0]) + "</b>",
			'item_name': "<b>" + str(s_key[1]) + "</b>",
			'uom': "<b>" + str(s_key[2]) + "</b>",
			'warehouse': None,
			'purchase_receipt': None,
			'indent': 0,
			'order_qty': "<b>" + str(total_or_qty) + "</b>",
			'receive_qty': "<b>" + str(total_rq_qty) + "</b>",
			'status': None
		})
		data.extend(lst)
	return data