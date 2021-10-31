# Copyright (c) 2021, RF and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from care.care.doctype.purchase_invoice_creation_tool.importer import Importer
from frappe.utils import nowdate

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
		start_import(self.name)
		return False

	@frappe.whitelist()
	def make_purchase_invoice(self):
		if self:
			i = Importer(self.reference_doctype, data_import=self)
			data = i.import_file.get_payloads_for_import()
			if len(data) > 0:
				pi = frappe.new_doc("Purchase Invoice")
				pi.supplier = self.supplier
				pi.posting_date = nowdate()
				pi.due_date = nowdate()
				pi.company = self.company
				pi.purchase_invoice_creation_tool = self.name
				pi.update_stock = 1
				for d in data:
					line = d.get('doc')
					item = frappe.get_doc("Item Supplier", {'supplier_part_no': line.get('supplier_item_code'), 'supplier': self.supplier})
					po_item = frappe.get_value("Purchase Order Item", {'item_code': item.parent, 'parent': self.purchase_order})
					if po_item:
						poi_doc = frappe.get_doc("Purchase Order Item", po_item)
						pi.append("items", {
							"item_code": item.parent,
							"warehouse": poi_doc.warehouse,
							"qty": line.get('qty'),
							"received_qty": line.get('qty'),
							"rate": line.get('rate'),
							"expense_account": poi_doc.expense_account,
							"conversion_factor": poi_doc.conversion_factor,
							"uom": poi_doc.uom,
							"stock_Uom": poi_doc.stock_uom,
							"purchase_order": self.purchase_order,
							"po_detail": poi_doc.name,
							"material_demand": poi_doc.material_demand,
							"material_demand_item": poi_doc.material_demand_item,
						})
					else:
						po_item
				pi.set_missing_values()
				pi.insert(ignore_permissions=True)
				return pi.as_dict()


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
