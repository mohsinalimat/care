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
		pri.brand,
		pri.item_name,
		pr.set_warehouse,
		pri.qty
		from `tabPurchase Receipt` as pr
		INNER JOIN `tabPurchase Receipt Item` as pri on pr.name = pri.parent"""

	if filters.get('posting_date'):
		query += " and pr.posting_date = '{0}'".format(filters.get('posting_date'))

	if filters.get('name'):
		query += " and pr.name = '{0}'".format(filters.get('name'))
	
	if filters.get('status'):
		query += " and pr.status = '{0}'".format(filters.get('status'))
	
	if filters.get('order_receiving'):
		query += " and pr.order_receiving = '{0}'" \
			.format(filters.get('order_receiving'))

	if filters.get('supplier'):
		supplier = tuple(filters.get('supplier'))
		query += " and pr.supplier in {0}".format(supplier)

	query += " order by pri.brand"

	result = frappe.db.sql(query, as_dict=True)
	data = []
	
	for row in result:
		data.append(row)
	return data
