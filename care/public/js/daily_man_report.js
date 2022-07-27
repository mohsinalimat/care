frappe.provide("care.daily_management");

care.daily_management = {
	"filters": get_filters(),
	onload: function(report) {
		care.daily_management.filters = get_filters()
		report.page.add_inner_button(__("Download Pdf Report"), function() {
			let url = "/api/method/care.care.report.daily_management_report.daily_management_report.download_pdf_report";
			open_url_post(url,{filters: report.get_values()}, true);
		}).addClass('btn-primary');
	}
};

function get_filters() {
	let filters = [
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

	return filters;
}
