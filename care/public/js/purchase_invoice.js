frappe.ui.form.on('Purchase Invoice', {
    refresh: function(frm, cdt, cdn) {
        cur_frm.fields_dict["items"].$wrapper.find('.grid-body .rows').find(".grid-row").each(function(i, item) {
            let d = locals[cur_frm.fields_dict["items"].grid.doctype][$(item).attr('data-name')];
            if(d["rate"] != d['price_list_rate']){
                $(item).find('.grid-static-col').css({'background-color': '#ffff80'});
            }
        });
	}
});