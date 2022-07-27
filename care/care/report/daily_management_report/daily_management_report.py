# Copyright (c) 2022, RF and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
	columns = get_column(filters)
	data = get_data(filters)
	return columns, data

def get_column(filters):
	if filters.get('type') == "Sales Summary":
		columns = [
			{"fieldname": "cost_center", "fieldtype": "Link", "label": "Branch", "options": "Cost Center", "width": 200},
			{"fieldname": "g_s_amt", "fieldtype": "Currency", "label": "Gross Sale Amount", "width": 180},
			{"fieldname": "g_s_count", "fieldtype": "Currency", "label": "Gross Sale Count", "width": 180},
			{"fieldname": "r_s_amt", "fieldtype": "Currency", "label": "Sale Return Amount", "width": 180},
			{"fieldname": "r_s_count", "fieldtype": "Currency", "label": "Gross Return Count", "width": 180},
			{"fieldname": "s_r_percent", "fieldtype": "Percent", "label": "Sales Return %", "width": 120},
			{"fieldname": "net_sales", "fieldtype": "Currency", "label": "Net Sales", "width": 180}
		]
		return columns

	if filters.get('type') == "Stock Summary":
		columns = [
			{"fieldname": "cost_center", "fieldtype": "Link", "label": "Branch", "options": "Cost Center", "width": 200},
			{"fieldname": "map", "fieldtype": "Currency", "label": "MAP", "width": 120},
			{"fieldname": "credit_sale", "fieldtype": "Currency", "label": "Credit Sale", "width": 130},
			{"fieldname": "credit_card", "fieldtype": "Currency", "label": "Credit Card", "width": 150},
			{"fieldname": "cash", "fieldtype": "Currency", "label": "Cash", "width": 150},
			{"fieldname": "local_purchase", "fieldtype": "Currency", "label": "Local Purchase", "width": 150},
			{"fieldname": "net_cash", "fieldtype": "Currency", "label": "Net Cash", "width": 150},
			{"fieldname": "closing_stock", "fieldtype": "Currency", "label": "Closing Stock", "width": 150}
		]
		return columns

	if filters.get('type') == "Profitability Analysis":
		columns = [
			{"fieldname": "cost_center", "fieldtype": "Link", "label": "Branch", "options": "Cost Center", "width": 180},
			{"fieldname": "net_revenue", "fieldtype": "Currency", "label": "Net Revenue", "width": 180},
			{"fieldname": "cost_sale", "fieldtype": "Currency", "label": "Cost of Sale", "width": 180},
			{"fieldname": "gp_margin", "fieldtype": "Percent", "label": "GP Margin", "width": 180}
		]
		return columns

def get_data(filters):
	if filters.get('type') == "Sales Summary":
		query = """select foo.cost_center,
			sum(foo.g_s_amt) as g_s_amt,
			sum(foo.g_s_count) as g_s_count,
			sum(foo.r_s_amt) as r_s_amt,
			sum(foo.r_s_count) as r_s_count,			
			(sum(foo.r_s_amt) / sum(foo.g_s_amt)) * 100 as s_r_percent,
			(sum(foo.g_s_amt) - sum(foo.r_s_amt)) as net_sales
			from (
				select cost_center,
				CASE
					when !is_return then sum(abs(rounded_total))
					else 0
				end as g_s_amt,
				CASE
					when !is_return then count(name)
					else 0
				end as g_s_count,
				CASE
					when is_return then sum(abs(rounded_total))
					else 0
				end as r_s_amt, 
				CASE
					when is_return then count(name)
					else 0
				end as r_s_count 
				from `tabSales Invoice`
				where docstatus = 1
				and cost_center != 'Corporate Office - CP'
				and company = "{0}"
				and posting_date <= "{1}"
				group by cost_center,is_return
			) as foo
			group by foo.cost_center""".format(filters.get('company'), filters.get('date'))

		result = frappe.db.sql(query, as_dict=True)
		t_g_s_amt = t_g_s_count = t_r_s_amt = t_r_s_count = 0
		for res in result:
			t_g_s_amt += res.g_s_amt
			t_g_s_count += res.g_s_count
			t_r_s_amt += res.r_s_amt
			t_r_s_count += res.r_s_count
		total = {
				"cost_center": '<b>Total</b>',
				"g_s_amt": t_g_s_amt,
				"g_s_count": t_g_s_count,
				"r_s_amt": t_r_s_amt,
				"r_s_count": t_r_s_count,
				"s_r_percent": 0 if t_g_s_amt == 0 else (t_r_s_amt / t_g_s_amt) * 100 ,
				"net_sales": t_g_s_amt - t_r_s_amt
				}
		result.append(total)
		return result
	if filters.get('type') == "Stock Summary":
		query = """select foo.cost_center, sum(foo.cash) as cash, sum(foo.map) as map , sum(foo.credit_card) as credit_card, sum(foo.citiledger) as credit_sale,
				0 as local_purchase,
				0 as net_cash,
				0 as closing_stock
				from (
					select cost_center,
					Case
						when account like '%cash%' then sum(debit_in_account_currency) - sum(credit_in_account_currency)
						else 0
					end as cash,
					Case
						when account like '%map%' then sum(debit_in_account_currency) - sum(credit_in_account_currency)
						else 0
					end as map,
					Case
						when account like '%credit card%' then sum(debit_in_account_currency) - sum(credit_in_account_currency)
						else 0
					end as credit_card,
					Case
						when account like '%citiledger%' then sum(debit_in_account_currency) - sum(credit_in_account_currency)
						else 0
					end as citiledger
					from `tabGL Entry`
					where cost_center is not null
					and is_cancelled = 0
					and cost_center != 'Corporate Office - CP' 
					and (account like '%cash%' or account like '%map%' or account like '%credit card%' or account like '%citiledger%')
					and company = "{0}"
					and posting_date <= "{1}"
					group by cost_center, account
				) as foo
				group by foo.cost_center""".format(filters.get('company'), filters.get('date'))
		result = frappe.db.sql(query, as_dict=True)
		t_cash = t_map = t_credit_card = t_credit_sale = t_local_purchase = t_closing_stock = 0
		for res in result:
			local_purchase = float(frappe.db.sql("""select sum(rounded_total) from `tabPurchase Receipt`
							where cost_center = '{0}' and docstatus = 1 
							and company = '{1}'
							and posting_date <= '{2}' """.format(res.cost_center,filters.get('company'), filters.get('date')))[0][0] or 0)
			closing_stock = float(frappe.db.sql("""select sum(stock_value) from `tabStock Ledger Entry` 
							where warehouse = '{0}' 
							and company = '{1}'
							and posting_date <= '{2}' 
							and is_cancelled = 0""".format(res.cost_center,filters.get('company'), filters.get('date')))[0][0] or 0)
			net_cash = res.cash + local_purchase
			res['local_purchase'] = local_purchase
			res['net_cash'] = net_cash
			res['closing_stock'] = closing_stock
			t_cash += res.cash
			t_map += res.map
			t_credit_card += res.credit_card
			t_credit_sale += res.credit_sale
			t_local_purchase += local_purchase
			t_closing_stock += closing_stock

		total = {
			"cost_center": "<b>Total</b>",
			"cash": t_cash,
			"map": t_map,
			"credit_card": t_credit_card,
			"credit_sale": t_credit_sale,
			"local_purchase": t_local_purchase,
			"net_cash": t_local_purchase + t_cash,
			"closing_stock": t_closing_stock
		}
		result.append(total)
		return result
	if filters.get('type') == "Profitability Analysis":
		query = """select foo.cost_center,
				sum(foo.g_s_amt) - sum(foo.r_s_amt)as net_revenue,
				0 as cost_sale,
				0 as gp_margin
				from (
					select cost_center,
					CASE
						when !is_return then sum(abs(rounded_total))
						else 0
					end as g_s_amt,
					CASE
						when is_return then sum(abs(rounded_total))
						else 0
					end as r_s_amt
					from `tabSales Invoice`
					where docstatus = 1
					and cost_center != 'Corporate Office - CP'
					and company = "{0}"
					and posting_date <= "{1}"
					group by cost_center,is_return
				) as foo
				group by foo.cost_center""".format(filters.get('company'), filters.get('date'))
		result = frappe.db.sql(query, as_dict=True)
		t_cost_sale = t_net_revenue = 0
		for res in result:
			cost_sale = float(frappe.db.sql("""select ifnull(sum(debit_in_account_currency) - sum(credit_in_account_currency), 0) 
						from `tabGL Entry` where cost_center = '{0}' 
						and account like '%Cost of Goods Sold%' 
						and is_cancelled = 0 
						and company = "{1}"
						and posting_date <= "{2}" """.format(res.cost_center, filters.get('company'), filters.get('date')))[0][0] or 0)
			res['cost_sale'] = cost_sale
			# res['gp_margin'] = 0 if res.net_revenue == 0 else (res.net_revenue + cost_sale) / res.net_revenue
			res['gp_margin'] = 0 if res.net_revenue == 0 else (1 - (cost_sale / res.net_revenue)) * 100
			t_cost_sale += cost_sale
			t_net_revenue += res.net_revenue

		total = {
			"cost_center": "<b>Total</b>",
			"net_revenue": t_net_revenue,
			"cost_sale": t_cost_sale,
			"gp_margin": 0 if t_net_revenue == 0 else (1 - (t_cost_sale / t_net_revenue)) * 100
		}
		result.append(total)
		return result