// Copyright (c) 2022, RF and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Pre-Order Info"] = {
	"filters": [
        {
			"fieldname":"warehouse",
			"label": __("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
			"reqd": 1
		},
        {
			"fieldname":"supplier",
			"label": __("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier"
		},
        {
			"fieldname":"base_on",
			"label": __("Order Qty Base On"),
			"fieldtype": "Select",
			"options": "Reorder Quantity\nOptimal Level",
			"default": "Optimal Level"
		}
	]
};
