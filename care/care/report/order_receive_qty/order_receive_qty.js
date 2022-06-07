// Copyright (c) 2022, RF and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Order Receive Qty"] = {
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
			"fieldname":"order_receiving",
			"label": __("Order Receiving"),
			"fieldtype": "Link",
			"options": "Order Receiving",
			"reqd": 1,
			"get_query": function () {
                return {
                    filters: {
                        docstatus: 1
                    }
                };
            }
		},
        {
			"fieldname":"item",
			"label": __("Item"),
			"fieldtype": "Link",
			"options": "Item"
		},
        {
			"fieldname":"warehouse",
			"label": __("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
			"get_query": function () {
                return {
                    filters: {
                        is_group: 0
                    }
                };
            }
		}
	]
};
