// Copyright (c) 2021, RF and contributors
// For license information, please see license.txt

frappe.ui.form.on('Order Receiving', {
	setup: function(frm, cdt, cdn) {
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
	    frm.trigger("apply_item_filter")
	},
	refresh: function(frm){
	    if (frm.doc.__islocal) {
			frm.set_value("date", frappe.datetime.now_date())
		}
		frm.trigger("apply_item_filter")
		frm.get_field("items").grid.toggle_display("split_qty", frm.doc.warehouse ? 0 : 1);
	    refresh_field("items");
	},
	warehouse: function(frm, cdt, cdn){
	    frm.get_field("items").grid.toggle_display("split_qty", frm.doc.warehouse ? 0 : 1);
	    refresh_field("items");
	},
	validate: function(frm, cdt, cdn){
	    update_total_qty(frm, cdt, cdn)
	},
    purchase_request: function (frm){
	    frm.trigger("apply_item_filter")
    },
    apply_item_filter: function (frm){
	    frappe.call({
            method: "get_item_code",
            doc: frm.doc,
            callback: function(r) {
                frm.fields_dict['items'].grid.get_field("item_code").get_query = function(doc, cdt, cdn) {
                    return {
                        filters: {'name':['in',r.message]}
                    }
                }
            }
        });
    },
});

function apply_child_btn_color(frm, cdt, cdn){
    frm.fields_dict["items"].$wrapper.find('.grid-body .rows').find(".grid-row").each(function(i, item) {
        $(item).find('.grid-static-col').find('.field-area').find('.form-group').find('.btn').css({'background-color': ' #2690ef','color': 'white'});
    });
    refresh_field("split_qty", cdn, "items");
}

frappe.ui.form.on('Order Receiving Item', {
    item_code: function(frm, cdt, cdn){
        var row = locals[cdt][cdn];
        if(!frm.doc.purchase_request || !frm.doc.supplier){
            frm.fields_dict["items"].grid.grid_rows[row.idx - 1].remove();
            frappe.msgprint(__("Select supplier first."))
        }
        else{
            if (row.item_code){
                frappe.run_serially([
                    ()=>update_price_rate(frm, cdt, cdn),
                    ()=>{
                        frappe.call({
                            method: "care.care.doctype.order_receiving.order_receiving.get_item_qty",
                            args: {
                                "purchase_request": frm.doc.purchase_request,
                                "item": row.item_code,
                                "supplier": frm.doc.supplier,
                                "warehouse": frm.doc.warehouse
                            },
                            callback: function(r) {
                                frappe.model.set_value(cdt,cdn,"qty",r.message);
                                refresh_field("qty", cdn, "items");
                            }
                        });
                    },
                    ()=>apply_pricing_rule(row, frm, cdt, cdn)
                ])

                var new_row = frm.fields_dict.items.grid;
                new_row.add_new_row(null, null, true, null, true);
                new_row.grid_rows[new_row.grid_rows.length - 1].toggle_editable_row();
                new_row.set_focus_on_row();
            }
        }
        apply_child_btn_color(frm, cdt, cdn)
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
	},
	split_qty: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
	    split_warehouse_wise_qty(row, frm, cdt, cdn)
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
    frappe.call({
        method: "erpnext.stock.get_item_details.get_conversion_factor",
        args: {
            item_code: item.item_code,
            uom: item.uom
        },
        callback: function(r) {
            if(!r.exc) {
                var conversion_factor = r.message.conversion_factor
                frappe.model.set_value(cdt,cdn,"conversion_factor",r.message.conversion_factor);
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
                            child_docname: item.name,
                            uom: item.uom,
                            stock_uom: item.stock_uom,
                            conversion_factor: conversion_factor
                        }
                    },
                    callback: function(r) {
                        frappe.model.set_value( cdt, cdn, 'rate',r.message)
                    }
                })
            }
        }
    });
}


function apply_pricing_rule(item, frm, cdt, cdn) {
    var args = _get_args(item, frm, cdt, cdn);
    return frm.call({
        method: "erpnext.accounts.doctype.pricing_rule.pricing_rule.apply_pricing_rule",
        args: {	args: args, doc: frm.doc },
        callback: function(r) {
            let data = r.message
            if (data[0].margin_type == 'Percentage' && data[0].discount_percentage > 0){
                frappe.model.set_value( cdt, cdn, 'discount_percent', data[0].discount_percentage)
            }
            else{
                frappe.model.set_value( cdt, cdn, 'discount_percent', 0)
            }
            if (data[0].margin_type == 'Amount' && data[0].discount_amount > 0){
                frappe.model.set_value( cdt, cdn, 'discount', data[0].discount_amount)
            }
            else{
                frappe.model.set_value( cdt, cdn, 'discount', 0)
            }
        }
    });
}

 function _get_args(item, frm, cdt, cdn) {
    return {
        "items": _get_item_list(item),
        "customer": frm.doc.customer || frm.doc.party_name,
        "quotation_to": frm.doc.quotation_to,
        "customer_group": frm.doc.customer_group,
        "territory": frm.doc.territory,
        "supplier": frm.doc.supplier,
        "supplier_group": frm.doc.supplier_group,
        "currency": frm.doc.currency,
        "conversion_rate": frm.doc.conversion_rate,
        "price_list": frm.doc.selling_price_list || frm.doc.buying_price_list,
        "price_list_currency": frm.doc.price_list_currency,
        "plc_conversion_rate": frm.doc.plc_conversion_rate,
        "company": frm.doc.company,
        "transaction_date": frm.doc.transaction_date || frm.doc.posting_date,
        "campaign": frm.doc.campaign,
        "sales_partner": frm.doc.sales_partner,
        "ignore_pricing_rule": frm.doc.ignore_pricing_rule,
        "doctype": frm.doc.doctype,
        "name": frm.doc.name,
        "is_return": cint(frm.doc.is_return),
        "update_stock": in_list(['Sales Invoice', 'Purchase Invoice'], frm.doc.doctype) ? cint(frm.doc.update_stock) : 0,
        "conversion_factor": frm.doc.conversion_factor,
        "pos_profile": frm.doc.doctype == 'Sales Invoice' ? frm.doc.pos_profile : '',
        "coupon_code": frm.doc.coupon_code
    };
}

function _get_item_list(item) {
    var item_list = [];
    var append_item = function(d) {
        if (d.item_code) {
            item_list.push({
                "doctype": d.doctype,
                "name": d.name,
                "child_docname": d.name,
                "item_code": d.item_code,
                "item_group": d.item_group,
                "brand": d.brand,
                "qty": d.qty,
                "stock_qty": d.stock_qty,
                "uom": d.uom,
                "stock_uom": d.stock_uom,
                "parenttype": d.parenttype,
                "parent": d.parent,
                "pricing_rules": d.pricing_rules,
                "warehouse": d.warehouse,
                "serial_no": d.serial_no,
                "batch_no": d.batch_no,
                "price_list_rate": d.price_list_rate,
                "conversion_factor": d.conversion_factor || 1.0
            });

            // if doctype is Quotation Item / Sales Order Iten then add Margin Type and rate in item_list
            if (in_list(["Quotation Item", "Sales Order Item", "Delivery Note Item", "Sales Invoice Item",  "Purchase Invoice Item", "Purchase Order Item", "Purchase Receipt Item"]), d.doctype) {
                item_list[0]["margin_type"] = d.margin_type;
                item_list[0]["margin_rate_or_amount"] = d.margin_rate_or_amount;
            }
        }
    };

    if (item) {
        append_item(item);
    } else {
        $.each(this.frm.doc["items"] || [], function(i, d) {
            append_item(d);
        });
    }
    return item_list;
}


function split_warehouse_wise_qty(row, frm, cdt, cdn){
    let data = JSON.parse(row.code || '[]')
    let dialog = new frappe.ui.Dialog({
        title: __('Split Qty'),
        fields: [
            {
                fieldtype: 'Float',
                fieldname: 'qty',
                label: __('Qty'),
                default: row.qty,
                read_only: 1
            },
            {
                fieldname: 'split_data',
                fieldtype: 'Table',
                label: __('Warehouses'),
                in_editable_grid: true,
                reqd: 1,
                fields: [{
                    fieldtype: 'Link',
                    fieldname: 'warehouse',
                    options: 'Warehouse',
                    in_list_view: 1,
                    label: __('Warehouse'),
                    get_query: () => {
                        return {
                            filters: {
                                "is_group": 0
                            }
                        };
                    }
                }, {
                    fieldtype: 'Float',
                    fieldname: 'qty',
                    label: __('Qty'),
                    in_list_view: 1,
                    reqd: 1,
                }],
                data: data
            },
        ],
        primary_action_label: __('Save'),
        primary_action: function(values) {
            let child_data = values.split_data;
            let t_qty = 0
            let lst = []
            child_data.forEach((d) => {
                t_qty = t_qty + d.qty
                lst.push({"warehouse": d.warehouse, "qty": d.qty})
            });
            if (values.qty != t_qty){
                frappe.throw(__("Total split qty must be equal to ") + values.qty);
            }
            else{
                dialog.hide();
                frappe.model.set_value(cdt,cdn,"code",JSON.stringify(lst));
                refresh_field("code", cdn, "items");
            }
        }
    });
    dialog.show();
}