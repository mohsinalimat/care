// Copyright (c) 2021, RF and contributors
// For license information, please see license.txt

frappe.ui.form.on('Order Receiving', {
	setup: function(frm) {
	    if (frm.doc.__islocal) {
			frm.set_value("date", frappe.datetime.now_date())
		}
		frm.set_value("buying_price_list", frappe.defaults.get_default('buying_price_list'))
		frm.set_value("currency", frappe.defaults.get_default('Currency'))
        frm.set_query("warehouse", () => {
			return {
				"filters": {
					"is_group": 0
				}
			};
		})
		frm.set_query("purchase_request", () => {
			return {
				"filters": {
					"docstatus": 1,
					"date": frm.doc.date
				}
			};
		})
		frm.set_query("supplier", function() {
            return {
                query: "care.care.doctype.purchase_invoice_creation_tool.purchase_invoice_creation_tool.get_supplier",
                filters: {'purchase_request': frm.doc.purchase_request}
            }
        });
	},
	refresh: function(frm){
	    if (frm.doc.__islocal) {
			frm.set_value("date", frappe.datetime.now_date())
		}
	},
	validate:function(frm, cdt, cdn){
	    update_total_qty(frm, cdt, cdn)
	}
});

frappe.ui.form.on('Order Receiving Item', {
    item_code: function(frm, cdt, cdn){
        var row = locals[cdt][cdn];
        if (row.item_code){
            update_price_rate(frm, cdt, cdn)
        }
    },
    qty: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        let amount = row.rate * row.qty
        frappe.model.set_value(cdt,cdn,"amount",amount);
        refresh_field("amount", cdn, "items");
        update_total_qty(frm, cdt, cdn)
	},
    rate: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        let amount = row.rate * row.qty
        frappe.model.set_value(cdt,cdn,"amount",amount);
        refresh_field("amount", cdn, "items");
        update_total_qty(frm, cdt, cdn)

	}
})

function update_total_qty(frm, cdt, cdn){
    let total_qty = 0
    let total_amt = 0
    $.each(frm.doc['items'] || [], function(i, row) {
        total_qty = total_qty + row.qty
        total_amt = total_amt + row.amount
    });
    frm.set_value("total_qty", total_qty);
    frm.set_value("total_amount", total_amt);
}

function update_price_rate(frm, cdt, cdn){
    var item = locals[cdt][cdn];
    frm.call({
        method: "care.hook_events.purchase_invoice.get_price_list_rate_for",
        args: {
            item_code: item.item_code,
            args: {
                item_code: item.item_code,
                supplier: frm.doc.supplier,
                currency: frm.doc.currency,
                price_list: frm.doc.buying_price_list,
                price_list_currency: frm.doc.currency,
                company: frm.doc.company,
                transaction_date: frm.doc.date ,
                doctype: frm.doc.doctype,
                name: frm.doc.name,
                qty: item.qty || 1,
                child_docname: item.name
            }
        },
        callback: function(r) {
            frappe.model.set_value( cdt, cdn, 'rate',r.message)
        }
    })
}