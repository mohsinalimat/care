frappe.listview_settings['Material Demand'] = {
	add_fields: ["status", "per_ordered", "per_received"],
	get_indicator: function(doc) {
		var precision = frappe.defaults.get_default("float_precision");
		if (doc.status=="Stopped") {
			return [__("Stopped"), "red", "status,=,Stopped"];
		} else if (doc.status=="Pending") {
			return [__("Pending"), "orange"];
		}else if (flt(doc.per_received, precision) < 100) {
            return [__("Partially Received"),'blue'];
        }else if (flt(doc.per_received, precision) == 100) {
            return [__("Received"), "green"];
        }
	}
};
