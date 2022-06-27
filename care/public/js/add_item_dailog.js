care.add_item_dialog = Class.extend({
	init: function(opts, show_dialog) {
		$.extend(this, opts);
//		let d = this.item;
		this.setup();
	},
	setup: function() {
//		this.item_code = this.item.item_code;
//		this.qty = this.item.qty;
		this.make_dialog();
		this.on_close_dialog();
	},
	make_dialog: function() {
		var me = this;
//		this.data = this.oldest ? this.oldest : [];
		let title = "Add Item";
		let fields = [
			{
				fieldname: 'start_date',
				fieldtype:'Date',
				label: __('Start Date'),
				reqd: 1,
				default: this.posting_date
			},
			{
				fieldname: 'end_date',
				fieldtype:'Date',
				label: __('End Date'),
				reqd: 1
			},
			{
				fieldname: 'no_of_visits',
				fieldtype:'Int',
				label: __('No of Visits'),
				reqd: 1
			},
			{fieldtype:'Column Break'},
		];
		this.dialog = new frappe.ui.Dialog({
			title: title,
			fields: fields
		});

		this.dialog.set_primary_action(__('Insert'), function() {
			me.values = me.dialog.get_values();
//			if(me.validate()) {
//			    let row = me.item;
//			    row.start_date = me.values.start_date
//			    row.end_date = me.values.end_date
//			    row.no_of_visits = me.values.no_of_visits
//			    row.service_team = me.values.service_team
//			    row.periodicity = me.values.periodicity
//			    row.location = me.values.location
//			    refresh_field("items");
//				me.dialog.hide()
//			}
		});
		this.dialog.show();
	},
	on_close_dialog: function() {
		this.dialog.get_close_btn().on('click', () => {
			this.on_close && this.on_close(this.item);
		});
	},
	validate: function() {
		let values = this.values;
		if(!values.start_date) {
			frappe.throw(__("Please select a Start Date"));
			return false;
		}
		if(!values.end_date) {
			frappe.throw(__("Please select a End Date"));
			return false;
		}
		if(!values.sales_person) {
			frappe.throw(__("Please select a Sales Person"));
			return false;
		}
		if(!values.no_of_visits) {
			frappe.throw(__("Please select a No. of Visit"));
			return false;
		}
		return true;
	}
});
