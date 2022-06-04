frappe.ui.form.on('Purchase Invoice', {
    setup: function (frm){
		frm.set_value("base_selling_price_list", frappe.defaults.get_default('selling_price_list'))
    },
    refresh: function(frm, cdt, cdn) {
        if(!frm.doc.base_selling_price_list){
            frm.set_value("base_selling_price_list", frappe.defaults.get_default('selling_price_list'))
        }
        // validate_item_rate(frm, cdt, cdn)
        if(!frm.doc__islocal && frm.doc.docstatus == 0)
        {
            frm.set_df_property('update_price_rate', 'hidden', 0);
            frm.fields_dict.update_price_rate.$input.addClass("btn-primary");
        }
        else{
            frm.set_df_property('update_price_rate', 'hidden', 1);
        }
        if (!frm.doc.franchise_inv_generated && frm.doc.docstatus ==1){
            frm.add_custom_button(__('Create Franchise Invoice'), function() {
                frm.call({
                    method: "care.hook_events.purchase_invoice.make_franchise_purchase_invoice",
                    args: {
                        "doc": frm.doc.name,
                        "method": null
                    },
                    callback: function (r) {
                        frm.reload_doc()
                    }
                })
            },__('Create'));
        }
	},
	// onload: function(frm, cdt, cdn){
	//      validate_item_rate(frm, cdt, cdn)
	// },
	// validate: function(frm, cdt, cdn){
	//      validate_item_rate(frm, cdt, cdn)
	// },
	update_price_rate: function(frm, cdt, cdn){
	    frappe.run_serially([
            () => frm.doc.items.forEach(function(item) {
                if(item.rate != item.price_list_rate){
                    let c_rate = item.rate;
                    frm.call({
                        method: "care.hook_events.purchase_invoice.get_price_list_rate_for",
                        args: {
                            item_code: item.item_code,
                            args: {
                                item_code: item.item_code,
                                barcode: item.barcode,
                                serial_no: item.serial_no,
                                batch_no: item.batch_no,
                                set_warehouse: frm.doc.set_warehouse,
                                warehouse: item.warehouse,
                                customer: frm.doc.customer || frm.doc.party_name,
                                quotation_to: frm.doc.quotation_to,
                                supplier: frm.doc.supplier,
                                currency: frm.doc.currency,
                                update_stock: frm.doc.update_stock,
                                conversion_rate: frm.doc.conversion_rate,
                                price_list: frm.doc.selling_price_list || frm.doc.buying_price_list,
                                price_list_currency: frm.doc.price_list_currency,
                                plc_conversion_rate: frm.doc.plc_conversion_rate,
                                company: frm.doc.company,
                                order_type: frm.doc.order_type,
                                is_pos: cint(frm.doc.is_pos),
                                is_return: cint(frm.doc.is_return),
                                is_subcontracted: frm.doc.is_subcontracted,
                                transaction_date: frm.doc.transaction_date || frm.doc.posting_date,
                                ignore_pricing_rule: frm.doc.ignore_pricing_rule,
                                doctype: frm.doc.doctype,
                                name: frm.doc.name,
                                project: item.project || frm.doc.project,
                                qty: item.qty || 1,
                                net_rate: item.rate,
                                stock_qty: item.stock_qty,
                                conversion_factor: item.conversion_factor,
                                weight_per_unit: item.weight_per_unit,
                                weight_uom: item.weight_uom,
                                manufacturer: item.manufacturer,
                                uom: item.uom,
                                stock_uom: item.stock_uom,
                                pos_profile: cint(frm.doc.is_pos) ? frm.doc.pos_profile : '',
                                cost_center: item.cost_center,
                                tax_category: frm.doc.tax_category,
                                item_tax_template: item.item_tax_template,
                                child_docname: item.name
                            }
                        },
                        callback: function(r) {
                            frappe.run_serially([
                                () => frappe.model.set_value(item.doctype, item.name, 'price_list_rate',r.message),
                                () => frappe.model.set_value(item.doctype, item.name, 'base_price_list_rate',r.message),
                                () => frappe.model.set_value(item.doctype, item.name, 'rate',c_rate)
                            ]);
                        }
                    })
                }
            }),
            () => frm.save()
        ])
	}
});

// function validate_item_rate(frm, cdt, cdn){
//     cur_frm.fields_dict["items"].$wrapper.find('.grid-body .rows').find(".grid-row").each(function(i, item) {
//         let d = locals[cur_frm.fields_dict["items"].grid.doctype][$(item).attr('data-name')];
//         if( d['price_list_rate'] - 1 <= d["rate"] && d["rate"] <= d['price_list_rate'] + 1){
//             $(item).find('.grid-static-col').css({'background-color': '#ffffff'});
//         }
//         else{
//             $(item).find('.grid-static-col').css({'background-color': '#ffff80'});
//         }
//     });
// }


frappe.ui.form.on('Purchase Invoice Item', {
    item_code: function(frm, cdt, cdn) {
         update_price_list(frm, cdt, cdn);
    },
    conversion_factor: function (frm, cdt, cdn){
        update_price_list(frm, cdt, cdn);
    }
})

function update_price_list(frm, cdt, cdn){
    var item = locals[cdt][cdn];
    if (item.item_code) {
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
                     transaction_date: frm.doc.date,
                     doctype: frm.doc.doctype,
                     name: frm.doc.name,
                     qty: item.qty || 1,
                     child_docname: item.name,
                     uom: item.uom,
                     stock_uom: item.stock_uom,
                     conversion_factor: item.conversion_factor
                 }
             },
             callback: function (r) {
                 frappe.model.set_value(cdt, cdn, 'selling_price_list_rate', r.message)
                 frappe.model.set_value(cdt, cdn, 'base_selling_price_list_rate', r.message)
             }
         })
    }
}
$.extend(cur_frm.cscript, {
    refresh: function(doc) {
		const me = this;
//		this._super();

		hide_fields(this.frm.doc);
		// Show / Hide button
		this.show_general_ledger();

		if(doc.update_stock==1 && doc.docstatus==1) {
			this.show_stock_ledger();
		}

		if(!doc.is_return && doc.docstatus == 1 && doc.outstanding_amount != 0){
			if(doc.on_hold) {
				this.frm.add_custom_button(
					__('Change Release Date'),
					function() {me.change_release_date()},
					__('Hold Invoice')
				);
				this.frm.add_custom_button(
					__('Unblock Invoice'),
					function() {me.unblock_invoice()},
					__('Create')
				);
			} else if (!doc.on_hold) {
				this.frm.add_custom_button(
					__('Block Invoice'),
					function() {me.block_invoice()},
					__('Create')
				);
			}
		}

		if(doc.docstatus == 1 && doc.outstanding_amount != 0
			&& !(doc.is_return && doc.return_against)) {
			this.frm.add_custom_button(__('Payment'), this.make_payment_entry, __('Create'));
			cur_frm.page.set_inner_btn_group_as_primary(__('Create'));
		}

		if(!doc.is_return && doc.docstatus==1) {
			if(doc.outstanding_amount >= 0 || Math.abs(flt(doc.outstanding_amount)) < flt(doc.grand_total)) {
				cur_frm.add_custom_button(__('Return / Debit Note'),
					this.make_debit_note, __('Create'));
			}

			if(!doc.auto_repeat) {
				cur_frm.add_custom_button(__('Subscription'), function() {
					erpnext.utils.make_subscription(doc.doctype, doc.name)
				}, __('Create'))
			}
		}

		if (doc.outstanding_amount > 0 && !cint(doc.is_return)) {
			cur_frm.add_custom_button(__('Payment Request'), function() {
				me.make_payment_request()
			}, __('Create'));
		}

		if(doc.docstatus===0) {
			this.frm.add_custom_button(__('Purchase Order'), function() {
				erpnext.utils.map_current_doc({
					method: "erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_invoice",
					source_doctype: "Purchase Order",
					target: me.frm,
					setters: {
						supplier: me.frm.doc.supplier || undefined,
						schedule_date: undefined
					},
					get_query_filters: {
						docstatus: 1,
						status: ["not in", ["Closed", "On Hold"]],
						per_billed: ["<", 99.99],
						company: me.frm.doc.company
					}
				})
			}, __("Get Items From"));

			this.frm.add_custom_button(__('Purchase Receipt'), function() {
			    me.frm.clear_table("taxes");
				erpnext.utils.map_current_doc({
					method: "care.hook_events.purchase_invoice.make_purchase_invoice",
					source_doctype: "Purchase Receipt",
					target: me.frm,
					setters: {
						supplier: me.frm.doc.supplier || undefined,
						posting_date: undefined
					},
					get_query_filters: {
						docstatus: 1,
						status: ["not in", ["Closed", "Completed", "Return Issued"]],
						company: me.frm.doc.company,
						is_return: 0
					}
				})
			}, __("Get Items From"));
		}
		this.frm.toggle_reqd("supplier_warehouse", this.frm.doc.is_subcontracted==="Yes");

		if (doc.docstatus == 1 && !doc.inter_company_invoice_reference) {
			frappe.model.with_doc("Supplier", me.frm.doc.supplier, function() {
				var supplier = frappe.model.get_doc("Supplier", me.frm.doc.supplier);
				var internal = supplier.is_internal_supplier;
				var disabled = supplier.disabled;
				if (internal == 1 && disabled == 0) {
					me.frm.add_custom_button("Inter Company Invoice", function() {
						me.make_inter_company_invoice(me.frm);
					}, __('Create'));
				}
			});
		}

		this.frm.set_df_property("tax_withholding_category", "hidden", doc.apply_tds ? 0 : 1);
	},
});
