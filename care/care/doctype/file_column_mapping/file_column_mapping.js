// Copyright (c) 2021, RF and contributors
// For license information, please see license.txt

frappe.ui.form.on('File Column Mapping', {
	// refresh: function(frm) {

	// }
});

frappe.ui.form.on('File Column Mapping Child', {
	column_position: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        let column_position = row.column_position
        for (var i = 0;i<frm.doc.field_mapping.length - 1;i++){
            if (column_position==frm.doc.field_mapping[i].column_position && row.idx - 1 != i){
                frappe.model.set_value(cdt,cdn,"column_position",null);
                refresh_field("column_position", cdn, "field_mapping");
                frappe.show_alert('Duplicate column position ' + column_position + ' not allow.')
            }
        }
	},
});
