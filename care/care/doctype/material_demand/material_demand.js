// Copyright (c) 2021, RF and contributors
// For license information, please see license.txt

frappe.ui.form.on('Material Demand', {
	 setup: function(frm) {
        frm.set_indicator_formatter('item_code',
			function(doc) { return (doc.stock_qty<=doc.ordered_qty) ? "green" : "orange"; });

	    frm.set_query("item_code", "items", function() {
			return {
				query: "erpnext.controllers.queries.item_query"
			};
		});
		frm.fields_dict['items'].grid.get_field('expense_account').get_query = function(doc) {
			return {
				filters: {
					'company': doc.company
				}
			}
		}
	 },
	 refresh: function(frm){
	     if(frm.doc.docstatus == 1 && frm.doc.per_ordered < 100 && frm.doc.status != "Received"){
             frm.add_custom_button(__('Make Purchase Order'), function(){
                frappe.call({
                    method: "make_purchase_order",
                    doc: frm.doc,
                    freeze: true,
                    callback: function(r) {
                        var doclist = frappe.model.sync(r.message);
                        frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
                    }
                });
             }, __('Create'));

             frm.add_custom_button(__('Make Purchase Invoice'), function(){
                frappe.call({
                    method: "make_purchase_invoice",
                    doc: frm.doc,
                    freeze: true,
                    callback: function(r) {
                        var doclist = frappe.model.sync(r.message);
                        frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
                    }
                });
             }, __('Create'));

             frm.page.set_inner_btn_group_as_primary(__('Create'));
         }

	 },
	 warehouse: function(frm) {
		let transaction_controller = new erpnext.TransactionController();
		transaction_controller.autofill_warehouse(frm.doc.items, "warehouse", frm.doc.warehouse);
	},
	schedule_date : function(frm) {
		if (frm.doc.schedule_date && frm.doc.items  && frm.doc.items .length) {
			let doctype = frm.doc.items [0].doctype;
			$.each(frm.doc.items  || [], function(i, item) {
				frappe.model.set_value(doctype, item.name, "schedule_date", frm.doc.schedule_date);
			});
		}
	}
});

frappe.ui.form.on('Material Demand Item', {
    qty: function(doc, cdt, cdn) {
        var row = locals[cdt][cdn];
        let amount = row.rate * row.qty
        frappe.model.set_value(cdt,cdn,"amount",amount);
        refresh_field("amount", cdn, "items");
        calculate_conversion(doc, cdt, cdn)
	},
    rate: function(doc, cdt, cdn) {
        var row = locals[cdt][cdn];
        let amount = row.rate * row.qty
        frappe.model.set_value(cdt,cdn,"amount",amount);
        refresh_field("amount", cdn, "items");
	},
	conversion_factor: function(doc, cdt, cdn) {
		calculate_conversion(doc, cdt, cdn)
	},
	uom: function(doc, cdt, cdn){
	    calculate_conversion(doc, cdt, cdn)
	}
})

function calculate_conversion(doc, cdt, cdn){
    var item = locals[cdt][cdn];
    if(item.item_code && item.uom) {
        return doc.call({
            method: "erpnext.stock.get_item_details.get_conversion_factor",
            args: {
                item_code: item.item_code,
                uom: item.uom
            },
            callback: function(r) {
                if(!r.exc) {
                    frappe.model.set_value(cdt,cdn,"conversion_factor",r.message.conversion_factor);
                    let stock_qty = flt(item.qty * r.message.conversion_factor, precision("stock_qty", item));
                    frappe.model.set_value(cdt,cdn,"stock_qty",stock_qty);
                    refresh_field("stock_qty", cdn, "items");
                    refresh_field("conversion_factor", cdn, "items");
                }
            }
        });
    }
}