frappe.ui.form.on('Payment Entry', {
    validate: function(frm){
        if(frm.doc.references){
            for (var row of frm.doc.references) {
                if (row.reference_doctype == "Purchase Invoice" || row.reference_doctype == "Sales Invoice") {
                    if (row.reference_doctype == "Purchase Invoice") {
                        var doctype = "Purchase Invoice";
                        var fieldname = "cost_center"
                    }
                    else if (row.reference_doctype == "Sales Invoice") {
                        var doctype = "Sales Invoice";
                        var fieldname = "cost_center";
                    }
                    get_sales_order(row, doctype, fieldname);
                }
            }
        }
    }
});

function get_sales_order(row, doctype, fieldname) {
	frappe.call({
		method: "frappe.client.get_value",
		args: {
			doctype: doctype,
			fieldname: fieldname,
			filters: { "name": row.reference_name }
		},
		callback: function (r) {
			if (r.message) {
				frappe.model.set_value(row.doctype, row.name, "cost_center", r.message.cost_center);
			}
		}
	});
}

