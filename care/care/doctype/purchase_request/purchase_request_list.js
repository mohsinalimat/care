frappe.listview_settings['Purchase Request'] = {
    add_fields: ["status"],
	get_indicator: function(doc) {
		if (doc.status== "Draft" ) {
			return [__("Draft" ), "orange"]
		}
		else if (doc.status== "Submitted" ) {
			return [__("Submitted" ), "green"]
		}
		else if (doc.status== "Cancelled" ) {
			return [__("Cancelled" ), "red"]
		}
		else if (doc.status== "Order Created" ) {
			return [__("Order Created" ), "purple"]
		}
	}
};
