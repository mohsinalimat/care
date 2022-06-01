frappe.listview_settings['Order Receiving'] = {
	add_fields: ["status"],
	get_indicator: function(doc) {
		var colors = {
			"Draft": "red",
			"Cancelled": "red",
			"Submitted": "blue",
			"Queue": "orange",
			"Return": "gray"
		};
		return [__(doc.status), colors[doc.status], "status,=," + doc.status];
	}
};