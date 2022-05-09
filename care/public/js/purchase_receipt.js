frappe.ui.form.on('Purchase Receipt', {
    refresh: function(frm) {
        if(frm.doc.taxes.length == 0 && frm.doc.taxes_and_charges){
            frm.trigger('taxes_and_charges');
        }
	},
    onload: function(frm, cdt, cdn) {
        if(frm.doc.taxes.length == 0 && frm.doc.taxes_and_charges){
            frm.trigger('taxes_and_charges');
        }
	}
});