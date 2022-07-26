// Copyright (c) 2022, RF and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Daily Managment Report"] = {
	"filters": [
        {
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname":"date",
			"label": __("Date"),
			"fieldtype": "Date",
			"width": "80",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
        {
			"fieldname":"type",
			"label": __("Report Type"),
			"fieldtype": "Select",
			"options": "Sales Summary\nStock Summary\nProfitability Analysis",
			"default": "Sales Summary",
			"reqd": 1
		}
	]
};
