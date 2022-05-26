// Copyright (c) 2021, RF and contributors
// For license information, please see license.txt

{% include 'care/public/js/tax_contoller.js' %};

//cur_frm.cscript.tax_table = "Purchase Taxes and Charges";

//{% include 'erpnext/accounts/doctype/purchase_taxes_and_charges_template/purchase_taxes_and_charges_template.js' %}

frappe.provide("care.care");

frappe.ui.form.on('Order Receiving', {
	setup: function(frm, cdt, cdn) {
	    if (frm.doc.__islocal) {
			frm.set_value("posting_date", frappe.datetime.now_date())
		}
		frm.set_value("buying_price_list", frappe.defaults.get_default('buying_price_list'))
		frm.set_value("currency", frappe.defaults.get_default('Currency'))
		frm.set_value("base_selling_price_list", frappe.defaults.get_default('selling_price_list'))
        frm.set_query("warehouse", () => {
			return {
				"filters": {
					"is_group": 0
				}
			};
		})
		frm.set_query("c_b_warehouse", () => {
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
					"date": frm.doc.posting_date
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
	    frm.set_query("taxes_and_charges", function() {
			return {
				filters: {'company': frm.doc.company }
			}
		});
	},
	refresh: function(frm, cdt, cdn){
	    if (frm.doc.__islocal) {
			frm.set_value("posting_date", frappe.datetime.now_date())
		}
		if(!frm.doc.base_selling_price_list){
            frm.set_value("base_selling_price_list", frappe.defaults.get_default('selling_price_list'))
        }
		apply_item_filters(frm)
		frm.get_field("items").grid.toggle_display("split_qty", frm.doc.warehouse ? 0 : 1);
		frm.get_field("items").grid.toggle_enable("rate", frm.doc.update_buying_price ? 1 : 0);
	    refresh_field("items");
	    validate_item_rate(frm, cdt, cdn)
	},
	warehouse: function(frm, cdt, cdn){
	    frm.get_field("items").grid.toggle_display("split_qty", frm.doc.warehouse ? 0 : 1);
	    refresh_field("items");
	},
	update_buying_price: function(frm, cdt, cdn){
		frm.get_field("items").grid.toggle_enable("rate", frm.doc.update_buying_price ? 1 : 0);
	    refresh_field("items");
	    if(!frm.doc.update_buying_price){
	        $.each(frm.doc['items'] || [], function(i, item) {
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
                            transaction_date: frm.doc.posting_date ,
                            doctype: frm.doc.doctype,
                            name: frm.doc.name,
                            qty: item.qty || 1,
                            child_docname: item.name,
                            uom: item.uom,
                            stock_uom: item.stock_uom,
                            conversion_factor: item.conversion_factor
                        }
                    },
                    callback: function(r) {
                        item.rate = r.message || 0
                        let amt = item.rate * item.qty
                        let discount_amount = (amt / 100) * item.discount_percent
                        let amount = amt - discount_amount
                        let dis_aft_rate = amount/ item.qty
                        item.amount = amount
                        item.net_amount = amount
                        item.base_net_amount = amount
                        item.discount = discount_amount
                        item.discount_after_rate = dis_aft_rate
                    }
                })
            });
	    }
	},
	validate: function(frm, cdt, cdn){
	    update_total_qty(frm, cdt, cdn)
	    validate_item_rate(frm, cdt, cdn)
	},
    purchase_request: function (frm){
	    apply_item_filters(frm)
    },
    onload: function (frm, cdt, cdn){
	    validate_item_rate(frm, cdt, cdn)
    }
});

function validate_item_rate(frm, cdt, cdn){
    cur_frm.fields_dict["items"].$wrapper.find('.grid-body .rows').find(".grid-row").each(function(i, item) {
        let d = locals[cur_frm.fields_dict["items"].grid.doctype][$(item).attr('data-name')];
        if( d['base_buying_price_list_rate'] - 1 <= d["rate"] && d["rate"] <= d['base_buying_price_list_rate'] + 1){
            $(item).find('.grid-static-col').css({'background-color': '#ffffff'});
        }
        else{
            $(item).find('.grid-static-col').css({'background-color': '#ffff80'});
        }
    });
}


function apply_item_filters(frm){
    console.log("apply_item_filters")
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
}

function apply_child_btn_color(frm, cdt, cdn){
    frm.fields_dict["items"].$wrapper.find('.grid-body .rows').find(".grid-row").each(function(i, item) {
        $(item).find('.grid-static-col').find('.field-area').find('.form-group').find('.btn').css({'background-color': ' #2690ef','color': 'white'});
    });
    refresh_field("split_qty", cdn, "items");
}

frappe.ui.form.on('Order Receiving Item', {
//    items_remove: function(frm, cdt, cdn){
//        apply_item_filters(frm)
//    },
    items_add: function(frm, cdt, cdn){
        apply_item_filters(frm)
    },
    item_code: function(frm, cdt, cdn){
        var row = locals[cdt][cdn];
        if(!frm.doc.purchase_request || !frm.doc.supplier){
            frm.fields_dict["items"].grid.grid_rows[row.idx - 1].remove();
            frappe.msgprint(__("Select supplier first."))
        }
        else{
            if (row.item_code){
                update_price_rate(frm, cdt, cdn),
                get_item_tax_template(frm, cdt, cdn)
                update_selling_price_rate(frm, cdt, cdn),
                apply_pricing_rule(row, frm, cdt, cdn),
                frappe.call({
                    method: "care.care.doctype.order_receiving.order_receiving.get_item_qty",
                    args: {
                        "purchase_request": frm.doc.purchase_request,
                        "item": row.item_code,
                        "supplier": frm.doc.supplier,
                        "warehouse": frm.doc.warehouse
                    },
                    callback: function(r) {
                         console.log("get Qty")
                        frappe.model.set_value(cdt,cdn,"qty",r.message);
                        refresh_field("qty", cdn, "items");
                    }
                });
            }
//            else{
//                apply_item_filters(frm)
//            }
        }
//        apply_child_btn_color(frm, cdt, cdn)
    },

    qty: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        update_amount(frm, cdt, cdn)
        update_total_qty(frm, cdt, cdn)
	},
    rate: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        frappe.model.set_value(cdt,cdn,"net_rate",row.rate);
        frappe.model.set_value(cdt,cdn,"base_net_rate",row.rate);
        update_amount(frm, cdt, cdn)
        update_total_qty(frm, cdt, cdn)
        calculate_margin(frm, cdt, cdn)
	},
    discount: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        let amt = row.rate * row.qty
        let discount_amount = (row.discount / amt) * 100
        frappe.model.set_value(cdt,cdn,"discount_percent",discount_amount);
        refresh_field("discount_percent", cdn, "items");
        update_amount(frm, cdt, cdn)
	},
    discount_percent: function(frm, cdt, cdn) {
        update_amount(frm, cdt, cdn)
	},
    selling_price_list_rate: function(frm, cdt, cdn) {
        calculate_margin(frm, cdt, cdn)
	},
	split_qty: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        frappe.call({
            method: "care.care.doctype.order_receiving.order_receiving.get_warehouse",
            args: {
                purchase_request:frm.doc.purchase_request,
                item:row.item_code
            },
            callback: function(r) {
                split_warehouse_wise_qty(row, frm, cdt, cdn, r.message)
            }
        });

	}
})

function update_amount(frm, cdt, cdn){
    var row = locals[cdt][cdn];
    let amt = row.rate * row.qty
    let discount_amount = (amt / 100) * row.discount_percent
    let amount = amt - discount_amount
    let dis_aft_rate = amount/ row.qty
    frappe.model.set_value(cdt,cdn,"amount",amount);
    frappe.model.set_value(cdt,cdn,"net_amount",amount);
    frappe.model.set_value(cdt,cdn,"base_net_amount",amount);
    frappe.model.set_value(cdt,cdn,"discount",discount_amount);
    frappe.model.set_value(cdt,cdn,"discount_after_rate",dis_aft_rate);
    refresh_field("amount", cdn, "items");
    refresh_field("net_amount", cdn, "items");
    refresh_field("base_net_amount", cdn, "items");
    refresh_field("discount", cdn, "items");
    refresh_field("discount_after_rate", cdn, "items");
}
function update_total_qty(frm, cdt, cdn){
    let total_qty = 0
    let total_amt = 0
    $.each(frm.doc['items'] || [], function(i, row) {
        total_qty = total_qty + row.qty
        total_amt = total_amt + row.amount
    });
    frm.set_value("total_qty", total_qty);
    frm.set_value("total", total_amt);
    frm.set_value("grand_total", total_amt);
}

function calculate_margin(frm, cdt, cdn){
     var item = locals[cdt][cdn];
     let margin = -100;
     if (item.selling_price_list_rate > 0){
        margin = (item.selling_price_list_rate - item.rate) / item.selling_price_list_rate * 100;
     }
     frappe.model.set_value( cdt, cdn, 'margin_percent',margin)
}

function update_price_rate(frm, cdt, cdn){
    console.log("update_price_rate")
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
                            transaction_date: frm.doc.posting_date ,
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
                        frappe.model.set_value( cdt, cdn, 'rate',r.message || 0)
                        frappe.model.set_value(cdt,cdn,"conversion_factor",conversion_factor || 0);
                        frappe.model.set_value( cdt, cdn, 'base_buying_price_list_rate',r.message || 0)
                    }
                })
            }
        }
    });
}

function update_selling_price_rate(frm, cdt, cdn){

    console.log("update_selling_price_rate")
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
                            price_list: frm.doc.base_selling_price_list,
                            price_list_currency: frm.doc.currency,
                            company: frm.doc.company,
                            transaction_date: frm.doc.posting_date ,
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
                        frappe.model.set_value( cdt, cdn, 'selling_price_list_rate',r.message || 0)
                        frappe.model.set_value( cdt, cdn, 'base_selling_price_list_rate',r.message || 0)
                    }
                })
            }
        }
    });
}


function apply_pricing_rule(item, frm, cdt, cdn) {
    console.log('apply_pricing_rule')
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

function split_warehouse_wise_qty(row, frm, cdt, cdn, warhs){
    let data = JSON.parse(row.code || '[]')
    if (data.length === 0){
        data = warhs;
    }
    let dialog = new frappe.ui.Dialog({
        title: __('Split Qty'),
        fields: [
            {
                fieldtype: 'Data',
                fieldname: 'item',
                 label: __('Item'),
                read_only: 1,
                default: row.item_code + ":" + row.item_name
            },
            { fieldtype: "Column Break" },
            {
                fieldtype: 'Float',
                fieldname: 'qty',
                label: __('Qty'),
                default: row.qty,
                read_only: 1
            },
            { fieldtype: "Section Break" },
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
                    columns: 4,
                    get_query: () => {
                        return {
                            filters: {
                                "is_group": 0
                            }
                        };
                    }
                }, {
                    fieldtype: 'Read Only',
                    fieldname: 'order_qty',
                    label: __('Order Qty'),
                    in_list_view: 1,
                    columns: 2
                }, {
                    fieldtype: 'Float',
                    fieldname: 'qty',
                    label: __('Qty'),
                    in_list_view: 1,
                    reqd: 1,
                    default: 0,
                    columns: 2
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
                lst.push({"warehouse": d.warehouse, "order_qty": d.order_qty, "qty": d.qty})
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

function get_item_tax_template(frm, cdt, cdn) {
    var item = frappe.get_doc(cdt, cdn);
    var update_stock = 0

    item.weight_per_unit = 0;
    item.weight_uom = '';
    // clear barcode if setting item (else barcode will take priority)
    if(item.item_code || item.barcode || item.serial_no) {
        frm.call({
            method: "care.care.doctype.order_receiving.order_receiving.get_item_tax_template",
            child: item,
            args: {
                item: item.item_code,
                args: {
                    item_code: item.item_code,
                    supplier: frm.doc.supplier,
                    currency: frm.doc.currency,
                    company: frm.doc.company,
                    transaction_date: frm.doc.posting_date,
                    doctype: frm.doc.doctype,
                    name: frm.doc.name,
                    qty: item.qty || 1,
                    net_rate: item.rate,
                    stock_qty: item.stock_qty,
                    conversion_factor: item.conversion_factor,
                    stock_uom: item.stock_uom,
                    child_docname: item.name
                }
            },

            callback: function(r) {
                if(!r.exc) {
                     frappe.model.set_value(cdt,cdn,"item_tax_template",r.message);
                }
            }
        });
    }
}
// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new care.care.ReceivingController({frm: cur_frm}));