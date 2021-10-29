# Copyright (c) 2021, RF and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.core.doctype.data_import.importer import Importer
from frappe.utils.background_jobs import enqueue

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

	def start_import(self):
		from frappe.core.page.background_jobs.background_jobs import get_info
		from frappe.utils.scheduler import is_scheduler_inactive

		start_import(self.name)
		# if is_scheduler_inactive() and not frappe.flags.in_test:
		# 	frappe.throw(
		# 		_("Scheduler is inactive. Cannot import data."), title=_("Scheduler Inactive")
		# 	)
		#
		# enqueued_jobs = [d.get("job_name") for d in get_info()]
		#
		# if self.name not in enqueued_jobs:
		# 	enqueue(
		# 		start_import,
		# 		queue="default",
		# 		timeout=6000,
		# 		event="data_import",
		# 		job_name=self.name,
		# 		data_import=self.name,
		# 		now=frappe.conf.developer_mode or frappe.flags.in_test,
		# 	)
		# 	return True

		return False

@frappe.whitelist()
def get_preview_from_template(data_import, import_file=None, google_sheets_url=None):
	return frappe.get_doc("Purchase Invoice Creation Tool", data_import).get_preview_from_template(
		import_file, google_sheets_url
	)

@frappe.whitelist()
def form_start_import(data_import):
	return frappe.get_doc("Purchase Invoice Creation Tool", data_import).start_import()

def start_import(data_import):
	"""This method runs in background job"""
	data_import = frappe.get_doc("Purchase Invoice Creation Tool", data_import)
	try:
		i = Importer(data_import.reference_doctype, data_import=data_import)
		# a = i.import_file.get_payloads_for_import()
		i.import_data()
	except Exception:
		frappe.db.rollback()
		data_import.db_set("status", "Error")
		frappe.log_error(title=data_import.name)
	finally:
		frappe.flags.in_import = False

	frappe.publish_realtime("data_import_refresh", {"data_import": data_import.name})
