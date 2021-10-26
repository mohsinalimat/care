// Copyright (c) 2021, RF and contributors
// For license information, please see license.txt

frappe.ui.form.on('Purchase Request', {
    setup: function(frm){
        if (!frm.doc.date){
            frm.set_value("date", frappe.datetime.get_today());
        }
    },
	refresh: function(frm) {
        frm.fields_dict.get_items.$input.addClass("btn-primary");
        if (frm.doc.docstatus == 1 || frm.doc.__islocal){
            frm.set_df_property('get_items', 'hidden', 1);
        }
        else{
            frm.set_df_property('get_items', 'hidden', 0);
        }
	},
	get_items: function(frm){
	    frappe.call({
            method: "get_items",
            doc: frm.doc,
            callback: function(r) {
                if(r.message) {
                    frm.clear_table("items");
                    r.message.forEach(function(d) {
                        let actual_qty = 0
                        if (d.actual_qty){
                            actual_qty = parseFloat(d.actual_qty)
                        }
                        let order_qty = 0
                        let avl_qty = parseFloat(d.warehouse_reorder_level) - parseFloat(actual_qty)
                        if (avl_qty > 0 && avl_qty < parseFloat(d.warehouse_reorder_level))
                        {
                            let total_qty = actual_qty + parseFloat(d.warehouse_reorder_qty)
                            if(total_qty > parseFloat(d.optimum_level)){
                                order_qty = parseFloat(d.optimum_level) - actual_qty
                            }
                            else{
                                order_qty = parseFloat(d.warehouse_reorder_qty)
                            }
                        }
                        if (order_qty > 0){
                            var item = frm.add_child("items");
                            item.item_code = d.item_code
                            item.item_name = d.item_name
                            item.brand = d.brand
                            item.item_description = d.description
                            item.stock_uom = d.stock_uom
                            item.reorder_level = parseFloat(d.warehouse_reorder_level)
                            item.optimal__level = parseFloat(d.optimum_level)
                            item.avl_qty = actual_qty
                            item.order_qty = order_qty
                            item.rate = d.last_purchase_rate
                            item.supplier = d.default_supplier
                            item.warehouse = d.warehouse
                            item.amount = d.last_purchase_rate * order_qty
                        }
                    })
                    refresh_field("items");
                }
            }
        });
	}
});

frappe.ui.form.on("Purchase Request Item", {
    order_qty: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        let amount = row.rate * row.order_qty
        frappe.model.set_value(cdt,cdn,"amount",amount);
        refresh_field("amount", cdn, "items");
	},
    rate: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        let amount = row.rate * row.order_qty
        frappe.model.set_value(cdt,cdn,"amount",amount);
        refresh_field("amount", cdn, "items");
	}
})

