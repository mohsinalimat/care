frappe.ui.form.on('Payment Entry', {
    validate: function(frm){
        frm.trigger('set_cost_center')
    },
    party: function(frm){
        var filters = {}
        frappe.run_serially([
            () => frm.events.get_outstanding_documents(frm, filters),
            () => frm.trigger('set_cost_center')
        ])
    },
    set_cost_center: function(frm){
        if(frm.doc.references){
            let grand_total = 0
            let out_total = 0
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
                    grand_total += row.total_amount
                    out_total += row.outstanding_amount
                    get_sales_order(row, doctype, fieldname);
                }
            }
            frm.set_value('grand_total', grand_total);
            frm.set_value('total_outstanding', out_total);
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

