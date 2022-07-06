// Copyright (c) 2022, RF and contributors
// For license information, please see license.txt

frappe.ui.form.on('HQ Transfer', {
    onload: function(frm){
        if (frm.doc.__islocal){
            frm.set_value("posting_date", frappe.datetime.get_today());
        }
    },
	refresh: function(frm) {
        frm.fields_dict.get_items.$input.addClass("btn-primary");
        frm.set_query("hq_warehouse", () => {
			return {
				"filters": {
					"is_group": 0
				}
			};
		})
	},
    get_items: function(frm){
        if(!frm.doc.hq_warehouse){
            frappe.throw("Select HQ Warehouse first!")
        }
    },
    get_items: function(frm, cdt, cdn){
        frappe.call({
            method: "get_items",
            doc: frm.doc,
            freeze: true,
            callback: function(r) {
                frm.clear_table("items");
                if(r.message) {
                    r.message.forEach(function(d) {
                        var item = frm.add_child("items");
                        item.item_code = d.item_code
                        item.item_name = d.item_name
                        item.uom = d.uom
                        item.stock_uom = d.stock_uom
                        item.conversion_factor = d.conversion_factor
                        item.stock_qty = d.stock_qty
                        item.avl_qty = d.avl_qty
                        item.rate = d.rate
                        item.qty = d.qty
                        item.allocated_qty = d.allocated_qty
                        item.amount = d.amount
                        item.code = JSON.stringify(d.code)
                    })
                }
                refresh_field("items");
            }
        });
	},
});

frappe.ui.form.on('HQ Transfer Item', {
    item_code: function(frm, cdt, cdn){
        var row = locals[cdt][cdn];
        if(!frm.doc.hq_warehouse){
            frm.fields_dict["items"].grid.grid_rows[row.idx - 1].remove();
            frappe.msgprint(__("Select HQ Warehouse first."))
        }
        if (row.item_code){
            get_items_details(frm, cdt, cdn)
        }
    },
    uom: function(frm, cdt, cdn){
        var row = locals[cdt][cdn];
        get_items_details(frm, cdt, cdn)
    },
    qty: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        update_amount(frm, cdt, cdn)
        update_total_qty(frm, cdt, cdn)
	},
    rate: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        update_amount(frm, cdt, cdn)
        update_total_qty(frm, cdt, cdn)
	},
	split_qty: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        split_warehouse_wise_qty(row, frm, cdt, cdn)
	}
});


function update_amount(frm, cdt, cdn){
    var row = locals[cdt][cdn];
    let amt = row.rate * row.qty
    frappe.model.set_value(cdt,cdn,"amount",amt);
    refresh_field("amount", cdn, "items");
}
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

function get_items_details(frm, cdt, cdn){
    var item = locals[cdt][cdn];
    frm.call({
        method: "care.care.doctype.hq_transfer.hq_transfer.get_items_details",
        args: {
            item_code: item.item_code,
            doc: frm.doc,
            item: item
        },
        callback: function(r) {
            frappe.model.set_value(cdt,cdn,"conversion_factor", r.message.conversion_factor || 0);
            frappe.model.set_value(cdt,cdn,"avl_qty", r.message.avl_qty || 0);
            frappe.model.set_value( cdt, cdn, 'rate', r.message.rate || 0)
            frappe.model.set_value( cdt, cdn, 'qty', r.message.demand || 0)
            frappe.model.set_value( cdt, cdn, 'stock_qty', r.message.stock_qty || 0)
            frappe.model.set_value( cdt, cdn, 'allocated_qty', r.message.allocated_qty || 0)
            frappe.model.set_value( cdt, cdn, 'code', JSON.stringify(r.message.code))
        }
    })
}

function split_warehouse_wise_qty(row, frm, cdt, cdn){
    let data = JSON.parse(row.code || '[]')
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
                fieldname: 'avl_qty',
                label: __('Avl Qty'),
                default: row.avl_qty,
                read_only: 1
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
            if (values.avl_qty < t_qty){
                frappe.throw(__("Total split qty must be equal to ") + values.avl_qty);
            }
            else{
                dialog.hide();
                frappe.model.set_value(cdt,cdn,"code",JSON.stringify(lst));
                frappe.model.set_value(cdt,cdn,"allocated_qty",t_qty);
                refresh_field("code", cdn, "items");
                refresh_field("allocated_qty", cdn, "items");
            }
        }
    });
    dialog.show();
}
