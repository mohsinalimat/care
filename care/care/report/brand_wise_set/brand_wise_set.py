# Copyright (c) 2013, Dexciss Technology and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import frappe, erpnext
from erpnext import get_company_currency, get_default_company
from erpnext.accounts.report.utils import get_currency, convert_to_presentation_currency
from frappe.utils import getdate, cstr, flt, fmt_money
from frappe import _, _dict
from erpnext.accounts.utils import get_account_currency
from erpnext.accounts.report.financial_statements import get_cost_centers_with_children
from six import iteritems
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_accounting_dimensions, get_dimension_with_children
from collections import OrderedDict

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
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"label": "Accepted Warehouse",
			"options": "Warehouse",
			"width": 170
		},
		{
			"fieldname": "accepted_quantity",
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

	if filters.get('name'):
		query += " and pr.name = '{0}'".format(filters.get('name'))
	
	if filters.get('status'):
		query += " and pr.status = '{0}'".format(filters.get('status'))
	
	query += " order by pri.brand"

	result = frappe.db.sql(query,as_dict=True)
	data = []
	
	for row in result:
		row = {
			"name": row.name,
			"brand": row.brand,
			"item_name": row.item_name,
			"warehouse": row.set_warehouse,
			"accepted_quantity": row.qty
		}
		data.append(row)
	return data