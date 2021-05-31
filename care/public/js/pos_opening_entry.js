frappe.ui.form.on('POS Opening Entry', {
    setup(frm) {
//		if (frm.doc.docstatus == 0) {
//			frm.trigger('set_posting_date_read_only');
//			frm.set_value('period_start_date', frappe.datetime.now_datetime());
//			frm.set_value('cashier', frappe.session.user);
//		}

//		frm.set_query("cashier", function(doc) {
//			return {
//				query: "erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry.get_cashiers",
//				filters: { 'parent': frm.doc._newname }
//			};
//		});
	},

});