// Copyright (c) 2022, RF and contributors
// For license information, please see license.txt
/* eslint-disable */
frappe.require("assets/care/js/daily_man_report.js", function() {

	frappe.query_reports["Daily Management Report"] = $.extend({},
		care.daily_management);

	frappe.query_reports["Daily Management Report"]["filters"].splice(8, 1);
});

