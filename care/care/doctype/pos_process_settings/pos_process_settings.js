// Copyright (c) 2021, RF and contributors
// For license information, please see license.txt

frappe.ui.form.on('POS Process Settings', {
    onload: function(frm) {
        if(!frm.doc.last_execution_time){
            frm.set_value('last_execution_time', frappe.datetime.now_datetime());
        }
    },
    refresh: function(frm) {
        if(!frm.doc.last_execution_time){
            frm.set_value('last_execution_time', frappe.datetime.now_datetime());
        }
    }
});
