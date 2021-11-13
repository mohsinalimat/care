# Copyright (c) 2013, RF and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data

def get_columns(filters):
	columns = [
		{
			"fieldname": "purchase_req",
			"fieldtype": "Link",
			"label": "Purchase Request",
			"options": "Purchase Request",
			"width": 120
		},
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
			"hidden":1
		},
		{
			"fieldname": "uom",
			"fieldtype": "Link",
			"label": "UOM",
			"options": "UOM",
			"width": 100
		},
		{
			"fieldname": "brand",
			"fieldtype": "Link",
			"label": "Brand",
			"options": "Brand",
			"width": 100
		},
		{
			"fieldname": "qty",
			"fieldtype": "Float",
			"label": "Order Qty",
			"width": 100
		},
		{
			"fieldname": "supplier",
			"fieldtype": "Link",
			"label": "Supplier",
			"options": "Supplier",
			"width": 120
		},
		{
			"fieldname": "supplier_name",
			"fieldtype": "Data",
			"label": "Supplier Name",
			"width": 200
		}
	]
	if filters.get('base_on') == "Warehouse":
		columns.append({
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"label": "Warehouse",
			"options": "Warehouse",
			"width": 200
		})
	return columns

def get_data(filters):

	query = """select pr.name as purchase_req,
			pri.item_code,
			pri.item_name,
			pri.brand,
			pr.order_uom as uom,
			sum(pri.order_qty) as qty,
			pri.supplier,
			s.supplier_name"""
	if filters.get('base_on') == "Warehouse":
		query += ",pri.warehouse"

	query += """ from `tabPurchase Request` pr 				
			inner join `tabPurchase Request Item` pri on pri.parent = pr.name 
			inner join `tabSupplier` s on s.name = pri.supplier 
			where
			pr.company = '{0}' and  
			pr.date between '{1}' and '{2}'""".format(filters.get('company'), filters.get('from_date'), filters.get('to_date'))

	if filters.get('item_code'):
		query += " and pri.item_code = '{0}'".format(filters.get('item_code'))

	if filters.get('warehouse'):
		query += " and pri.warehouse = '{0}'".format(filters.get('warehouse'))

	if filters.get('supplier'):
		query += " and pri.supplier = '{0}'".format(filters.get('supplier'))

	query += """ group by pr.name, pri.item_code,pri.item_name,pri.brand,pr.order_uom,
				pri.supplier,s.supplier_name"""
	if filters.get('base_on') == "Warehouse":
		query += ",pri.warehouse"

	query += " order by pr.name, pri.item_code"
	result = frappe.db.sql(query, as_dict=True)
	return result