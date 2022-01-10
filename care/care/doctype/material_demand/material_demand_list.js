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
	},
	onload: function(list_view) {
	    const action = () => {
            const selected_docs = list_view.get_checked_items();
            const docnames = list_view.get_checked_items(true);
            open_url_post(
                '/api/method/care.hook_events.make_xlsx_file.build_xlsx_response',
                {
                    material_demand_lst: docnames
                }
            );
        };
	    list_view.page.add_actions_menu_item(__('Export Excel'), action, false);
	}
};
