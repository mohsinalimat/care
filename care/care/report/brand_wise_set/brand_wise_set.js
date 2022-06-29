// Copyright (c) 2022, RF and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Brand Wise Set"] = {
	"filters": [
		{
			"fieldname": "posting_date",
			"fieldtype": "Date",
			"label": "Posting Date",
			"mandatory": 0,
			"options": "Purchase Receipt"
		},
		{
			"fieldname": "item_name",
			"fieldtype": "Data",
			"label": "Item Name",
			"mandatory": 0,
		},
		// {
		// 	"fieldname":"status",
		// 	"label": __("Status"),
		// 	"fieldtype": "Select",
		// 	"options": ["", __("Draft"), __("To Bill"), __("Completed"), __("Return Issued"), __("Cancelled"), __("Closed")]
		// },
		{
			"fieldname":"order_receiving",
			"label": __("Order Receiving"),
			"fieldtype": "MultiSelectList",
			get_data: function(txt) {
				return frappe.db.get_link_options('Order Receiving', txt);
			}
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
