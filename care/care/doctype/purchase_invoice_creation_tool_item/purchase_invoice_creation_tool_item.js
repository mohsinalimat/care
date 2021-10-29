// Copyright (c) 2021, RF and contributors
// For license information, please see license.txt

frappe.ui.form.on('Purchase Invoice Creation Tool Item', {
	 onload: function(frm) {
        frm.disable_save();
	 },
	 refresh: function(frm) {
        frm.disable_save();
	 }
});
