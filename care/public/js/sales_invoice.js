frappe.ui.form.on('Sales Invoice', {
    refresh: function(frm, cdt, cdn) {
//        cur_frm.fields_dict["items"].$wrapper.find('.grid-body .rows').find(".grid-row").each(function(i, item) {
//            let d = locals[cur_frm.fields_dict["items"].grid.doctype][$(item).attr('data-name')];
//            if(d["rate"] != d['price_list_rate']){
//                $(item).find('.grid-static-col').css({'background-color': '#ffff80'});
//            }
//        });
        if (!frm.doc.franchise_inv_gen && frm.doc.docstatus ==1 && frm.doc.is_franchise_inv ==1){
            frm.add_custom_button(__('Create Franchise Invoice'), function() {
                frm.call({
                    method: "care.hook_events.sales_invoice.create_franchise_inv",
                    args: {
                        doc_name: frm.doc.name
                    },
                    callback: function (r) {
                        frm.reload_doc()
                    }
                })
            },__('Create'));
        }
	}
});