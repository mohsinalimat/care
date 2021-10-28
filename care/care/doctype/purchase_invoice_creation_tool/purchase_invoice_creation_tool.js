// Copyright (c) 2021, RF and contributors
// For license information, please see license.txt

frappe.ui.form.on('Purchase Invoice Creation Tool', {
	 setup: function(frm) {
        frm.has_import_file = () => {
			return frm.doc.import_file;
		};
	 },
	download_template(frm) {
		frappe.require('/assets/js/data_import_tools.min.js', () => {
			frm.data_exporter = new frappe.data_import.DataExporter(
				frm.doc.reference_doctype,
				frm.doc.import_type
			);
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

		frappe.require('/assets/js/data_import_tools.min.js', () => {
			frm.import_preview = new frappe.data_import.ImportPreview({
				wrapper: frm.get_field('import_preview').$wrapper,
				doctype: frm.doc.reference_doctype,
				preview_data,
				import_log,
				frm,
				events: {
					remap_column(changed_map) {
					    console.log("------------------------",changed_map)
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
});
