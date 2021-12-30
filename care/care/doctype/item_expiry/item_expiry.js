// Copyright (c) 2021, RF and contributors
// For license information, please see license.txt

frappe.ui.form.on('Item Expiry', {
	// refresh: function(frm) {

	// }
});

frappe.ui.form.on('Item Expiry Child', {
	item_code: function (frm,cdt,cdn){
	    frappe.model.set_value( cdt, cdn, 'add_date',frappe.datetime.now_datetime())
    }
});
