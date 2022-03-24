frappe.listview_settings['Purchase Invoice Creation Tool'] = {
    add_fields: ["status"],
	get_indicator: function(doc) {
		if (doc.status== "Pending" ) {
			return [__("Pending" ), "orange"]
		}
		else if (doc.status== "Not Started" ) {
			return [__("Not Started" ), "orange"]
		}
		else if (doc.status== "Partial Success" ) {
			return [__("Partial Success" ), "orange"]
		}
		else if (doc.status== "Success" ) {
			return [__("Success" ), "green"]
		}
		else if (doc.status== "In Progress" ) {
			return [__("In Progress" ), "orange"]
		}
		else if (doc.status== "Error" ) {
			return [__("Error" ), "red"]
		}
		else if (doc.status== "Invoice Created" ) {
			return [__("Invoice Created" ), "purple"]
		}
		else if (doc.status== "Receipt Created" ) {
			return [__("Receipt Created" ), "purple"]
		}
	}
};
