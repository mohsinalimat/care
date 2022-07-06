# Copyright (c) 2013, Dexciss Technology and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	columns = [
		{
			"fieldname": "name",
			"fieldtype": "Link",
			"label": "ID",
			"options": "Purchase Receipt",
			"width": 170
		},
		{
			"fieldname": "supplier_name",
			"fieldtype": "Data",
			"label": "Supplier Name",
			"width": 170
		},
		{
			"fieldname": "brand",
			"fieldtype": "Link",
			"label": "Brand",
			"options": "Brand",
			"width": 150
		},
		{
			"fieldname": "item_name",
			"fieldtype": "Data",
			"label": "Item Name",
			"width": 170
		},
		{
			"fieldname": "set_warehouse",
			"fieldtype": "Link",
			"label": "Accepted Warehouse",
			"options": "Warehouse",
			"width": 170
		},
		{
			"fieldname": "qty",
			"fieldtype": "Float",
			"label": "Accepted Quantity",
			"width": 120
		}
	]
	return columns


def get_data(filters):
	
	query = """select 
		pr.name,
		pr.supplier_name,
		pri.brand,
		pri.item_name,
		pr.set_warehouse,
		pri.qty
		from `tabPurchase Receipt` as pr
		INNER JOIN `tabPurchase Receipt Item` as pri on pr.name = pri.parent
		where pr.docstatus = 1"""

	if filters.get('posting_date'):
		query += " and pr.posting_date = '{0}'".format(filters.get('posting_date'))

	if filters.get('item_name'):
		query += " and pri.item_name like '%{0}%'".format(filters.get('item_name'))
	
	# if filters.get('status'):
	# 	query += " and pr.status = '{0}'".format(filters.get('status'))
	
	if filters.get('order_receiving'):
		order_receiving = tuple(filters.get('order_receiving'))
		if len(order_receiving) == 1:
			query += " and pr.order_receiving = '{0}'".format(order_receiving[0])
		else:
			query += " and pr.order_receiving in {0} ".format(order_receiving)
	
	if filters.get('supplier'):
		supplier = tuple(filters.get('supplier'))
		if len(supplier) == 1:
			query += " and pr.supplier = '{0}'".format(supplier[0])
		else:
			query += " and pr.supplier in {0} ".format(supplier)

	query += " order by pr.set_warehouse, pri.brand, pri.item_name"

	result = frappe.db.sql(query, as_dict=True)
	data = []
	
	for row in result:
		data.append(row)
	return data
