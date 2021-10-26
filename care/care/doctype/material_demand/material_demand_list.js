frappe.listview_settings['Material Demand'] = {
	add_fields: ["status", "per_ordered", "per_received"],
	get_indicator: function(doc) {
		var precision = frappe.defaults.get_default("float_precision");
		if (doc.status=="Stopped") {
			return [__("Stopped"), "red", "status,=,Stopped"];
		} else if (doc.docstatus==1 && flt(doc.per_ordered, precision) == 0) {
			return [__("Pending"), "orange", "per_ordered,=,0"];
		}  else if (doc.docstatus==1 && flt(doc.per_ordered, precision) < 100) {
			return [__("Partially ordered"), "yellow", "per_ordered,<,100"];
		}else if (flt(doc.per_received, precision) < 100 && flt(doc.per_received, precision) > 0) {
            return [__("Partially Received"), "yellow", "per_received,<,100"];
        }else if (flt(doc.per_received, precision) == 100) {
            return [__("Received"), "green", "per_received,=,100"];
        } else if (flt(doc.per_ordered, precision) >= 100 && flt(doc.per_received, precision) == 0) {
            return [__("Ordered"), "green", "per_ordered,=,100"];
        }
	}
};
