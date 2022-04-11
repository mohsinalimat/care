// Copyright (c) 2021, RF and contributors
// For license information, please see license.txt

frappe.ui.form.on('Purchase Invoice Creation Tool', {
	setup: function(frm) {
        frm.has_import_file = () => {
			 return frm.doc.import_file;
		};
		if (frm.doc.__islocal) {
			frm.set_df_property('section_break_10', 'hidden', 1);
			frm.set_value("date", frappe.datetime.now_date())
		}
		frm.set_query("purchase_request", () => {
			return {
				"filters": {
					"docstatus": 1,
					"date": frm.doc.date
//					"status": "Order Created"
				}
			};
		})
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
		frm.set_query("supplier", function() {
            return {
                query: "care.care.doctype.purchase_invoice_creation_tool.purchase_invoice_creation_tool.get_supplier",
                filters: {'purchase_request': frm.doc.purchase_request}
            }
        });
	},
	download_template(frm) {
		frappe.require('/assets/care/js/data_import_tools1.min.js', () => {
			frm.data_exporter = new frappe.data_import.DataExporter(
				frm.doc.reference_doctype,
				frm.doc.import_type
			);
		});
	},
	refresh: function(frm){
	    if (frm.doc.__islocal) {
			frm.set_df_property('section_break_10', 'hidden', 1);
			frm.set_value("date", frappe.datetime.now_date())
		}
		else{
		    frm.set_df_property('section_break_10', 'hidden', 0);
		}

        frm.trigger('import_file');
	    if (frm.doc.status != "Invoice Created" && frm.doc.status != "Receipt Created"){
            if (frm.doc.status != "Success"){
                frm.trigger('show_import_log');
                let label = __('Validate File');
                frm.page.set_primary_action(label, () => frm.events.start_import(frm));
            }
            if (frm.doc.status == "Success"){
                let label = __('Make Purchase Receipt');
                frm.page.set_primary_action(label, () => frm.events.make_purchase_invoice(frm));
            }
        }
        else{
            frm.disable_save();
        }
        if(frm.doc.status == "Success" || frm.doc.status == "Invoice Created" || frm.doc.status == "Receipt Created"){
            frm.set_df_property('import_file', 'read_only', 1);
        }
        else{
            frm.set_df_property('import_file', 'read_only', 0);
        }
	},
	make_purchase_invoice(frm){
        frappe.call({
            method: "make_purchase_invoice",
            doc: frm.doc,
            freeze: true,
            callback: function(r) {
                if( r.message){
//                    frm.set_value("status", "Invoice Created")
//                    refresh_field("status");
//                    frm.save();
                    frappe.set_route("List", "Purchase Receipt", {
                        purchase_invoice_creation_tool: frm.doc.name,
                    })
                }
            }
        });
	},
	start_import(frm) {
		frm
			.call({
				method: 'form_start_import',
				args: { data_import: frm.doc.name },
				btn: frm.page.btn_primary
			})
			.then(r => {
				if (r.message === true) {
					frm.disable_save();
				}
				frm.reload_doc()
			});
	},
	import_file(frm) {
		frm.toggle_display('section_import_preview', frm.has_import_file());
		if (!frm.has_import_file()) {
			frm.get_field('import_preview').$wrapper.empty();
			return;
		} else {
			frm.trigger('update_primary_action');
		}

		// load import preview
		frm.get_field('import_preview').$wrapper.empty();
		$('<span class="text-muted">')
			.html(__('Loading import file...'))
			.appendTo(frm.get_field('import_preview').$wrapper);
		frm
			.call({
				method: 'get_preview_from_template',
				args: {
					data_import: frm.doc.name,
					import_file: frm.doc.import_file
				},
				error_handlers: {
					TimestampMismatchError() {
						// ignore this error
					}
				}
			})
			.then(r => {
				let preview_data = r.message;
				frm.events.show_import_preview(frm, preview_data);
				frm.events.show_import_warnings(frm, preview_data);
			});
		if(frm.doc.status == "Pending"){
		    frm.trigger('set_column_mapping')
		}
	},
	show_import_preview(frm, preview_data) {
		let import_log = JSON.parse(frm.doc.import_log || '[]');

		if (
			frm.import_preview &&
			frm.import_preview.doctype === frm.doc.reference_doctype
		) {
			frm.import_preview.preview_data = preview_data;
			frm.import_preview.import_log = import_log;
			frm.import_preview.refresh();
			return;
		}

		frappe.require('/assets/care/js/data_import_tools1.min.js', () => {
			frm.import_preview = new frappe.data_import.ImportPreview({
				wrapper: frm.get_field('import_preview').$wrapper,
				doctype: frm.doc.reference_doctype,
				preview_data,
				import_log,
				frm,
				events: {
					remap_column(changed_map) {
						let template_options = JSON.parse(frm.doc.template_options || '{}');
						template_options.column_to_field_map = template_options.column_to_field_map || {};
						Object.assign(template_options.column_to_field_map, changed_map);
						frm.set_value('template_options', JSON.stringify(template_options));
						frm.save().then(() => frm.trigger('import_file'));
					}
				}
			});
		});
	},
	show_import_warnings(frm, preview_data) {
		let columns = preview_data.columns;
		let warnings = JSON.parse(frm.doc.template_warnings || '[]');
		warnings = warnings.concat(preview_data.warnings || []);

		frm.toggle_display('import_warnings_section', warnings.length > 0);
		if (warnings.length === 0) {
			frm.get_field('import_warnings').$wrapper.html('');
			return;
		}

		// group warnings by row
		let warnings_by_row = {};
		let other_warnings = [];
		for (let warning of warnings) {
			if (warning.row) {
				warnings_by_row[warning.row] = warnings_by_row[warning.row] || [];
				warnings_by_row[warning.row].push(warning);
			} else {
				other_warnings.push(warning);
			}
		}

		let html = '';
		html += Object.keys(warnings_by_row)
			.map(row_number => {
				let message = warnings_by_row[row_number]
					.map(w => {
						if (w.field) {
							let label =
								w.field.label +
								(w.field.parent !== frm.doc.reference_doctype
									? ` (${w.field.parent})`
									: '');
							return `<li>${label}: ${w.message}</li>`;
						}
						return `<li>${w.message}</li>`;
					})
					.join('');
				return `
				<div class="warning" data-row="${row_number}">
					<h5 class="text-uppercase">${__('Row {0}', [row_number])}</h5>
					<div class="body"><ul>${message}</ul></div>
				</div>
			`;
			})
			.join('');

		html += other_warnings
			.map(warning => {
				let header = '';
				if (warning.col) {
					let column_number = `<span class="text-uppercase">${__('Column {0}', [warning.col])}</span>`;
					let column_header = columns[warning.col].header_title;
					header = `${column_number} (${column_header})`;
				}
				return `
					<div class="warning" data-col="${warning.col}">
						<h5>${header}</h5>
						<div class="body">${warning.message}</div>
					</div>
				`;
			})
			.join('');
		frm.get_field('import_warnings').$wrapper.html(`
			<div class="row">
				<div class="col-sm-10 warnings">${html}</div>
			</div>
		`);
	},
	show_import_log(frm) {
		let import_log = JSON.parse(frm.doc.import_log || '[]');
		let logs = import_log;
		frm.toggle_display('import_log', false);
		frm.toggle_display('import_log_section', logs.length > 0);

		if (logs.length === 0) {
			frm.get_field('import_log_preview').$wrapper.empty();
			return;
		}

		let rows = logs
			.map(log => {
				let html = '';
				if (log.success) {
					if (frm.doc.import_type === 'Insert New Records') {
						html = __('Successfully imported {0}', [
							`<span class="underline">${frappe.utils.get_form_link(
								frm.doc.reference_doctype,
								log.docname,
								true
							)}<span>`
						]);
					} else {
						html = __('Successfully updated {0}', [
							`<span class="underline">${frappe.utils.get_form_link(
								frm.doc.reference_doctype,
								log.docname,
								true
							)}<span>`
						]);
					}
				} else {
					let messages = log.messages
						.map(JSON.parse)
						.map(m => {
							let title = m.title ? `<strong>${m.title}</strong>` : '';
							let message = m.message ? `<div>${m.message}</div>` : '';
							return title + message;
						})
						.join('');
					let id = frappe.dom.get_unique_id();
					html = `${messages}
						<button class="btn btn-default btn-xs" type="button" data-toggle="collapse" data-target="#${id}" aria-expanded="false" aria-controls="${id}" style="margin-top: 15px;">
							${__('Show Traceback')}
						</button>
						<div class="collapse" id="${id}" style="margin-top: 15px;">
							<div class="well">
								<pre>${log.exception}</pre>
							</div>
						</div>`;
				}
				let indicator_color = log.success ? 'green' : 'red';
				let title = log.success ? __('Success') : __('Failure');

				if (frm.doc.show_failed_logs && log.success) {
					return '';
				}

				return `<tr>
					<td>${log.row_indexes.join(', ')}</td>
					<td>
						<div class="indicator ${indicator_color}">${title}</div>
					</td>
					<td>
						${html}
					</td>
				</tr>`;
			})
			.join('');

		if (!rows && frm.doc.show_failed_logs) {
			rows = `<tr><td class="text-center text-muted" colspan=3>
				${__('No failed logs')}
			</td></tr>`;
		}

		frm.get_field('import_log_preview').$wrapper.html(`
			<table class="table table-bordered">
				<tr class="text-muted">
					<th width="10%">${__('Row Number')}</th>
					<th width="10%">${__('Status')}</th>
					<th width="80%">${__('Message')}</th>
				</tr>
				${rows}
			</table>
		`);
	},
	show_failed_logs(frm) {
		frm.trigger('show_import_log');
	},
	supplier: function(frm){
	    frm.trigger('set_column_mapping')
	},
	set_column_mapping: function(frm){
	    frappe.call({
            method: "set_column_mapping",
            doc: frm.doc,
            callback: function(r) {
                if(r.message){
                    frm.set_value('template_options',JSON.stringify(r.message))
                }
            }
        });
	}
});
