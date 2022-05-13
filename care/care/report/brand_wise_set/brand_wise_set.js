// Copyright (c) 2022, RF and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Brand Wise Set"] = {
	"filters": [
		{
			"fieldname": "name",
			"fieldtype": "Link",
			"label": "Name",
			"mandatory": 0,
			"options": "Purchase Receipt"
		},
		{
			"fieldname":"status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": ["", __("Draft"), __("To Bill"), __("Completed"), __("Return Issued"), __("Cancelled"), __("Closed")]
		},
	]
};
