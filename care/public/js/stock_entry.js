
frappe.ui.form.on('Stock Entry', {
    set_expense_account: function(frm, cdt, cdn) {
       set_warehouse_in_children(frm.doc.items, "expense_account", frm.doc.set_expense_account);
	}
});

frappe.ui.form.on('Stock Entry Detail', {
    item_code: function(frm, cdt, cdn) {
    	if (frm.doc.set_expense_account && frm.doc.is_material_return){
    		frappe.model.set_value( cdt, cdn, 'expense_account',frm.doc.set_expense_account)
		}
	},
	items_add: function (frm, cdt, cdn) {
    	if (frm.doc.set_expense_account && frm.doc.is_material_return){
    		frappe.model.set_value( cdt, cdn, 'expense_account',frm.doc.set_expense_account)
		}
	}
});

function set_warehouse_in_children(child_table, warehouse_field, warehouse) {
	let transaction_controller = new erpnext.TransactionController();
	transaction_controller.autofill_warehouse(child_table, warehouse_field, warehouse);
}

erpnext.stock.StockEntry = erpnext.stock.StockController.extend({
	toggle_related_fields: function(doc) {
		this.frm.toggle_enable("from_warehouse", doc.purpose!='Material Receipt');
		this.frm.toggle_enable("to_warehouse", doc.purpose!='Material Issue');

		this.frm.fields_dict["items"].grid.set_column_disp("retain_sample", doc.purpose=='Material Receipt');
		this.frm.fields_dict["items"].grid.set_column_disp("sample_quantity", doc.purpose=='Material Receipt');

		this.frm.cscript.toggle_enable_bom();

		if (doc.purpose == 'Send to Subcontractor') {
			doc.customer = doc.customer_name = doc.customer_address =
				doc.delivery_note_no = doc.sales_invoice_no = null;
		}
		else if (doc.is_material_return){
			doc.customer = doc.customer_name = doc.customer_address =
				doc.delivery_note_no = doc.sales_invoice_no = doc.purchase_receipt_no =
				doc.address_display = null;
		}
		else {
			doc.customer = doc.customer_name = doc.customer_address =
				doc.delivery_note_no = doc.sales_invoice_no = doc.supplier =
				doc.supplier_name = doc.supplier_address = doc.purchase_receipt_no =
				doc.address_display = null;
		}
		if(doc.purpose == "Material Receipt") {
			this.frm.set_value("from_bom", 0);
		}

		// Addition costs based on purpose
		this.frm.toggle_display(["additional_costs", "total_additional_costs", "additional_costs_section"],
			doc.purpose!='Material Issue');

		this.frm.fields_dict["items"].grid.set_column_disp("additional_cost", doc.purpose!='Material Issue');
	}
})
$.extend(cur_frm.cscript, new erpnext.stock.StockEntry({frm: cur_frm}));
