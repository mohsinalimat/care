# Copyright (c) 2022, RF and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
	columns = get_column()
	data = get_data(filters)
	return columns, data

def get_column():
	columns = [
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
			"width": 180
		},
		{
			"fieldname": "cost_center",
			"fieldtype": "Link",
			"label": "Cost Center",
			"options": "Cost Center",
			"width": 250
		},
		{
			"fieldname": "purchase",
			"fieldtype": "Currency",
			"label": "Purchase",
			"width": 150
		},
		{
			"fieldname": "payment",
			"fieldtype": "Currency",
			"label": "Payment",
			"width": 150
		},
		{
			"fieldname": "balance",
			"fieldtype": "Currency",
			"label": "Balance",
			"width": 150
		}
	]
	return columns

def get_data(filters):
	query = """ select 
		foo.supplier,
		foo.supplier_name,
		foo.cost_center,
		sum(foo.purchase) as purchase,
		sum(foo.payment) as payment,
		sum(foo.purchase) - sum(foo.payment) as balance 
		from
		(select pi.supplier, 
		pi.supplier_name, 
		c.parent_cost_center as cost_center, 
		pi.grand_total as purchase,
		0 as payment
		from `tabPurchase Invoice` as pi
		inner join `tabCost Center` as c on c.name = pi.cost_center   
		where pi.docstatus = 1 
		and pi.company = '{0}' 
		and pi.posting_date between '{1}' and '{2}' """.format(filters.get('company'),filters.get('from_date'),
													filters.get('to_date'))
	if filters.get('cost_center'):
		query += " and c.parent_cost_center = '{0}' ".format(filters.get('cost_center'))

	query += """ UNION 
		select pe.party as supplier, 
		pe.party_name as supplier_name, 
		c.parent_cost_center as cost_center, 
		0 as purchase,
		pe.paid_amount as payment
		from `tabPayment Entry` pe		
		inner join `tabCost Center` as c on c.name = pe.cost_center 
		where pe.docstatus = 1 
		and pe.payment_type = 'Pay' 
		and pe.company = '{0}' 
		and pe.posting_date between '{1}' and '{2}' """.format(filters.get('company'),filters.get('from_date'),
													filters.get('to_date'))
	if filters.get('cost_center'):
		query += " and c.parent_cost_center = '{0}' ".format(filters.get('cost_center'))

	query += """ ) as foo 
		where foo.cost_center is not null 
		group by foo.supplier, foo.supplier_name, foo.cost_center 
		order by foo.cost_center """

	result = frappe.db.sql(query, as_dict=True)
	return result
