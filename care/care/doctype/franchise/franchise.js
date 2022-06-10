// Copyright (c) 2022, RF and contributors
// For license information, please see license.txt

frappe.ui.form.on('Franchise', {
    setup: function(frm) {
        frm.fields_dict['franchise_list'].grid.get_field("warehouse").get_query = function(doc, cdt, cdn) {
            return {
                filters: {
                    is_group: 0,
                    is_franchise: 1
                }
            }
        }
    },
    refresh: function(frm){
        frm.fields_dict.sync_data.$input.addClass("btn-primary");
    },
    sync_data: function(frm){
        frappe.call({
            method: "sync_data_on_franchise",
            doc: frm.doc,
            freeze: true,
            freeze_message: __("Uploading data on Franchise...")
            callback: function(r) {
                frappe.msgprint(__('Data uploaded successfully'));
            }
        });
    }
});
