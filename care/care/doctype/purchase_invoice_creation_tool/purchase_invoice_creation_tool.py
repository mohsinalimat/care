# Copyright (c) 2021, RF and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from care.care.doctype.purchase_invoice_creation_tool.importer import Importer
from care.care.doctype.purchase_invoice_creation_tool.exporter import Exporter
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
				purchase_order = frappe.get_doc("Purchase Order", {'supplier': self.supplier, 'purchase_request': self.purchase_request})
				if self.warehouse:
					for d in data:
						line = d.get('doc')
						item = None
						item_code = None
						if line.get('item_code'):
							item = frappe.get_doc("Item", line.get('item_code'))
							item_code = item.name
						else:
							item = frappe.get_doc("Item Supplier", {'supplier_part_no': line.get('supplier_item_code'), 'supplier': self.supplier})
							item_code = item.parent

						po_item = frappe.get_doc("Purchase Order Item", {'item_code': item_code, 'parent': purchase_order.name, "warehouse": self.warehouse})
						if po_item:
							poi_doc = frappe.get_doc("Purchase Order Item", po_item.name)
							margin_type = None
							if line.get("discount_percent"):
								margin_type = "Percentage"
							if line.get("discount"):
								margin_type = "Amount"

							pi.append("items", {
								"item_code": item_code,
								"warehouse": poi_doc.warehouse,
								"qty": line.get('qty'),
								"received_qty": line.get('qty'),
								"rate": line.get('rate'),
								"expense_account": poi_doc.expense_account,
								"conversion_factor": poi_doc.conversion_factor,
								"uom": poi_doc.uom,
								"stock_Uom": poi_doc.stock_uom,
								"purchase_order": purchase_order.name,
								"po_detail": poi_doc.name,
								"material_demand": poi_doc.material_demand,
								"material_demand_item": poi_doc.material_demand_item,
								"margin_type": margin_type,
								"discount_percentage": line.get("discount_percent"),
								"discount_amount": line.get("discount"),
							})
						else:
							po_item
				else:
					for d in data:
						line = d.get('doc')
						item = None
						item_code = None
						if line.get('item_code'):
							item = frappe.get_doc("Item", line.get('item_code'))
							item_code = item.name
						else:
							item = frappe.get_doc("Item Supplier", {'supplier_part_no': line.get('supplier_item_code'), 'supplier': self.supplier})
							item_code = item.parent

						po_item = frappe.get_list("Purchase Order Item", {'item_code': item_code, 'parent': purchase_order.name}, ['name'])
						received_qty = float(line.get('qty'))
						for p_tm in po_item:
							if received_qty > 0:
								poi_doc = frappe.get_doc("Purchase Order Item", p_tm.name)
								if poi_doc:
									margin_type = None
									if line.get("discount_percent"):
										margin_type = "Percentage"
									if line.get("discount"):
										margin_type = "Amount"

									pi.append("items", {
										"item_code": item_code,
										"warehouse": poi_doc.warehouse,
										"qty": poi_doc.qty,
										"received_qty": poi_doc.qty if poi_doc.qty <= received_qty else received_qty,
										"rate": line.get('rate'),
										"expense_account": poi_doc.expense_account,
										"conversion_factor": poi_doc.conversion_factor,
										"uom": poi_doc.uom,
										"stock_Uom": poi_doc.stock_uom,
										"purchase_order": purchase_order.name,
										"po_detail": poi_doc.name,
										"material_demand": poi_doc.material_demand,
										"material_demand_item": poi_doc.material_demand_item,
										"margin_type": margin_type,
										"discount_percentage": line.get("discount_percent"),
										"discount_amount": line.get("discount"),
									})
									received_qty -= poi_doc.qty
								else:
									poi_doc
				pi.set_missing_values()
				pi.insert(ignore_permissions=True)
				return pi.as_dict()


@frappe.whitelist()
def download_template(
	doctype, export_fields=None, export_records=None, export_filters=None, file_type="CSV"
):
	"""
	Download template from Exporter
		:param doctype: Document Type
		:param export_fields=None: Fields to export as dict {'Sales Invoice': ['name', 'customer'], 'Sales Invoice Item': ['item_code']}
		:param export_records=None: One of 'all', 'by_filter', 'blank_template'
		:param export_filters: Filter dict
		:param file_type: File type to export into
	"""

	export_fields = frappe.parse_json(export_fields)
	export_filters = frappe.parse_json(export_filters)
	export_data = export_records != "blank_template"

	e = Exporter(
		doctype,
		export_fields=export_fields,
		export_data=export_data,
		export_filters=export_filters,
		file_type=file_type,
		export_page_length=5 if export_records == "5_records" else None,
	)
	e.build_response()


@frappe.whitelist()
def download_errored_template(data_import_name):
	data_import = frappe.get_doc("Data Import", data_import_name)
	data_import.export_errored_rows()

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


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_supplier(doctype, txt, searchfield, start, page_len, filters):
	if filters.get('purchase_request'):
		result = frappe.db.sql("""select s.name, s.supplier_name
					from `tabSupplier` as s 
					inner join `tabPurchase Multi Supplier` as ms on ms.supplier = s.name
					where ms.parent= %s""", (filters.get('purchase_request')))
		return result
	else:
		return ("", )