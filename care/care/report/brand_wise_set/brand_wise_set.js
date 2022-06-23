// Copyright (c) 2022, RF and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Brand Wise Set"] = {
	"filters": [
		{
			"fieldname": "posting_date",
			"fieldtype": "Link",
			"label": "Posting Date",
			"mandatory": 0,
			"options": "Purchase Receipt"
		},
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
		{
			"fieldname": "order_receiving",
			"fieldtype": "Link",
			"label": "Order Receiving",
			"mandatory": 0,
			"options": "Order Receiving"
		},
		{
			"fieldname":"supplier",
			"label": __("Supplier"),
			"fieldtype": "MultiSelectList",
			get_data: function(txt) {
				return frappe.db.get_link_options('Supplier', txt);
			}
		}
	]
};
