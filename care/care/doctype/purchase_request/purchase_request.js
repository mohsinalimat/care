// Copyright (c) 2021, RF and contributors
// For license information, please see license.txt

frappe.ui.form.on('Purchase Request', {
    setup: function(frm){
        if (!frm.doc.date){
            frm.set_value("date", frappe.datetime.get_today());
        }
    },
    onload: function(frm){
        if (frm.doc.__islocal){
            frappe.call({
                method: "get_warehouse",
                doc: frm.doc,
                callback: function(r) {
                    if(r.message) {
                        frm.clear_table("warehouses");
                        r.message.forEach(function(d) {
                            var w = frm.add_child("warehouses");
                            w.warehouse = d.name
                            w.order_per = d.order_per
                        });
                        refresh_field("warehouses");
                    }
                }
            });
        }
    },
	refresh: function(frm) {
	    if (!frm.doc.date){
            frm.set_value("date", frappe.datetime.get_today());
        }
        frm.fields_dict.get_items.$input.addClass("btn-primary");
        if (frm.doc.docstatus == 1 || frm.doc.__islocal){
            frm.set_df_property('get_items', 'hidden', 1);
        }
        else{
            frm.set_df_property('get_items', 'hidden', 0);
        }
        if(frm.doc.docstatus == 1){
            frm.add_custom_button(__('Make Purchase Order'), function(){
                frappe.call({
                    method: "make_purchase_order",
                    doc: frm.doc,
                    freeze: true,
                    callback: function(r) {
                        frappe.set_route('List', 'Purchase Order', {purchase_request: frm.doc.name});
                    }
                });
            }).addClass("btn-primary");
        }
        if(frm.doc.status == 'Open'){
            frm.add_custom_button(__('Closed'), function(){
                frm.doc.status = 'Closed'
                frm.dirty();
			    frm.save_or_update();
            });
        }
        if(frm.doc.status == 'Closed'){
            frm.add_custom_button(__('Re-Open'), function(){
                frm.doc.status = 'Open'
                frm.dirty();
			    frm.save_or_update();
            });
        }
        if(frm.doc.docstatus !=0){
            frm.add_custom_button(__('Download Excel'), function(){
                open_url_post(
					'/api/method/care.care.doctype.purchase_request.purchase_request.download_excel',
					{
						purchase_request: frm.doc.name
					}
				);
            }, __("Downloads"));
            frm.add_custom_button(__('Download Excel Summary'), function(){
                open_url_post(
					'/api/method/care.care.doctype.purchase_request.purchase_request.download_excel_summary',
					{
						purchase_request: frm.doc.name
					}
				);
            }, __("Downloads"));
         }
	},
	get_items: function(frm, cdt, cdn){
	    frappe.call({
            method: "get_items",
            doc: frm.doc,
            callback: function(r) {
                frm.clear_table("items");
                if(r.message) {
                    r.message.forEach(function(d) {
                        let order_qty = parseFloat(d.order_qty)
                        if (order_qty > 0){
                            let pack_order_qty = Math.ceil(order_qty / parseFloat(d.conversion_factor))
                            var item = frm.add_child("items");
                            item.item_code = d.item_code
                            item.item_name = d.item_name
                            item.brand = d.brand
                            item.item_description = d.description
                            item.stock_uom = d.stock_uom
                            item.reorder_level = parseFloat(d.warehouse_reorder_level)
                            item.optimal__level = parseFloat(d.optimum_level)
                            item.avl_qty = d.actual_qty
                            item.order_qty = order_qty
                            item.pack_order_qty = pack_order_qty
                            item.conversion_factor = d.conversion_factor
                            item.rate = d.last_purchase_rate
                            item.supplier = d.default_supplier
                            item.warehouse = d.warehouse
                            item.amount = d.last_purchase_rate * pack_order_qty
                            item.avl_stock_qty_corp = d.avl_stock_qty_corp
                        }
                    })
                }
                refresh_field("items");
                frm.save();
            }
        });
	},
	suppliers: function(frm){
//        frm.clear_table("items");
//        refresh_field("items");
	    frappe.call({
            method: "get_suppliers_name",
            doc: frm.doc,
            callback: function(r) {
                frm.set_value("supplier_name", r.message);
            }
        });
	},
	supplier: function(frm, cdt, cdn){
	    if(frm.doc.supplier){
            frm.clear_table("suppliers");
            refresh_field("suppliers");
            var supplier = frm.add_child("suppliers")
            supplier.supplier = frm.doc.supplier
            refresh_field("suppliers");
            frm.trigger('suppliers')
            for (var i = 0; i < frm.doc.items.length; i++) {
                var item = frm.doc.items[i]
                item.supplier = frm.doc.supplier;
            }
            refresh_field("items");
	    }
	},
	warehouses: function(frm){
        frm.clear_table("items");
        refresh_field("items");
	},
	validate: function(frm){
	    var total_amt = 0.0
	    frm.doc.items.forEach(function(d){
	        total_amt += parseFloat(d.amount)
	    })
	    frm.set_value("total_amount", total_amt)
	    refresh_field("total_amount")
	}
});

frappe.ui.form.on("Purchase Request Item", {
    order_qty: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        let pack_order_qty = Math.ceil(row.order_qty / parseFloat(row.conversion_factor))
        frappe.model.set_value(cdt,cdn,"pack_order_qty",pack_order_qty);
        let amount = row.rate * pack_order_qty
        frappe.model.set_value(cdt,cdn,"amount",amount);
        refresh_field("pack_order_qty", cdn, "items");
        refresh_field("amount", cdn, "items");
	},
    pack_order_qty: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        let order_qty = Math.ceil(row.pack_order_qty * parseFloat(row.conversion_factor))
        row.order_qty = order_qty
        let amount = row.rate * row.pack_order_qty
        frappe.model.set_value(cdt,cdn,"amount",amount);
        refresh_field("order_qty", cdn, "items");
        refresh_field("amount", cdn, "items");
	},
    rate: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        let amount = row.rate * row.order_qty
        frappe.model.set_value(cdt,cdn,"amount",amount);
        refresh_field("amount", cdn, "items");
	},
	item_code: function(frm, cdt, cdn){
	    var item = locals[cdt][cdn];
	    if(item.item_code) {
            return frm.call({
                method: "erpnext.stock.get_item_details.get_conversion_factor",
                args: {
                    item_code: item.item_code,
                    uom: frm.doc.order_uom
                },
                callback: function(r) {
                    if(!r.exc) {
                        frappe.model.set_value(cdt,cdn,"conversion_factor",r.message.conversion_factor);
                        refresh_field("conversion_factor", cdn, "items");
                        update_price_rate(item,frm, cdt, cdn);
                    }

                }
            });
        }
	}
})

function update_price_rate(item,frm, cdt, cdn){
    frm.call({
        method: "care.hook_events.purchase_invoice.get_price_list_rate_for",
        args: {
            item_code: item.item_code,
            args: {
                item_code: item.item_code,
                supplier: item.supplier,
                currency: frappe.defaults.get_default('Currency'),
                price_list: frappe.defaults.get_default('buying_price_list'),
                price_list_currency: frappe.defaults.get_default('Currency'),
                company: frm.doc.company,
                transaction_date: frm.doc.date ,
                doctype: frm.doc.doctype,
                name: frm.doc.name,
                qty: item.qty || 1,
                child_docname: item.name,
                uom: frm.doc.order_uom,
                stock_uom: item.stock_uom,
                conversion_factor: item.conversion_factor
            }
        },
        callback: function(r) {
            frappe.model.set_value( cdt, cdn, 'rate',r.message || 0)
        }
    })
}