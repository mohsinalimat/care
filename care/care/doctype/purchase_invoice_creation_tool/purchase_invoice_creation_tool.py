# Copyright (c) 2021, RF and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.core.doctype.data_import.importer import Importer

class PurchaseInvoiceCreationTool(Document):
	@frappe.whitelist()
	def get_preview_from_template(self, import_file=None, google_sheets_url =None):
		if import_file:
			self.import_file = import_file

		if not self.import_file:
			return

		i = self.get_importer()
		a = i.get_data_for_import_preview()
		return a

	def get_importer(self):
		return Importer(self.reference_doctype, data_import=self)

@frappe.whitelist()
def get_preview_from_template(data_import, import_file=None, google_sheets_url=None):
	return frappe.get_doc("Purchase Invoice Creation Tool", data_import).get_preview_from_template(
		import_file, google_sheets_url
	)