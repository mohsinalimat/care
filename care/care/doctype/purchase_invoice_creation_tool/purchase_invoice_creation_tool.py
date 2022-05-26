# Copyright (c) 2021, RF and contributors
# For license information, please see license.txt

import frappe
from frappe import _, scrub
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
				material_demand = frappe.get_list("Material Demand", {'supplier': self.supplier, 'purchase_request': self.purchase_request}, ['name'])
				m_list = []
				for res in material_demand:
					m_list.append(res.name)
				count = 0
				bonus_un_odr = []
				if self.warehouse:
					is_franchise = frappe.get_value("Warehouse", {'name': self.warehouse}, "is_franchise")
					cost_center = frappe.get_value("Warehouse", {'name': self.warehouse}, "cost_center")
					pi = frappe.new_doc("Purchase Receipt")
					pi.supplier = self.supplier
					pi.posting_date = nowdate()
					pi.due_date = nowdate()
					pi.company = self.company
					pi.purchase_invoice_creation_tool = self.name
					pi.purchase_request = self.purchase_request
					pi.cost_center = cost_center
					pi.update_stock = 1 if not is_franchise else 0
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

						md_item = frappe.get_value("Material Demand Item", {'item_code': item_code, 'parent': ['in', m_list], "warehouse": self.warehouse}, "name")
						if md_item:
							md_doc = frappe.get_doc("Material Demand Item", md_item)
							margin_type = None
							if line.get("discount_percent"):
								margin_type = "Percentage"
							if line.get("discount"):
								margin_type = "Amount"

							pi.append("items", {
								"item_code": item_code,
								"warehouse": md_doc.warehouse,
								"qty": line.get('qty'),
								"received_qty": line.get('qty'),
								"rate": line.get('rate'),
								"expense_account": md_doc.expense_account,
								"cost_center": md_doc.cost_center,
								"uom": md_doc.uom,
								"stock_Uom": md_doc.stock_uom,
								"material_demand": md_doc.parent,
								"material_demand_item": md_doc.name,
								"margin_type": margin_type,
								"discount_percentage": line.get("discount_percent"),
								"discount_amount": line.get("discount"),
							})

						else:
							if self.ignore_un_order_item:
								pass
							else:
								frappe.throw(_("Item <b>{0}</b> not found in Material Demand").format(item_code))

						if line.get('bonus'):
							bonus_un_odr.append(frappe._dict({
								"item_code": item_code,
								"warehouse": self.c_b_warehouse,
								"qty": line.get('bonus'),
								"is_free_item": 1,
								"rate": line.get('rate'),
								"discount_percentage": line.get("discount_percent"),
								"discount_amount": line.get("discount"),
								"uom": "Pack",
								"stock_Uom": "Nos",
							}))
					if pi.get('items'):
						pi.set_missing_values()
						pi.insert(ignore_permissions=True)
						count = 1

				else:
					item_details = {}
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

						md_item = frappe.get_list("Material Demand Item", {'item_code': item_code, 'parent': ['in', m_list]}, ['name'])
						received_qty = float(line.get('qty'))
						if md_item:
							for p_tm in md_item:
								if received_qty > 0:
									md_doc = frappe.get_doc("Material Demand Item", p_tm.name)
									if md_doc:
										margin_type = None
										if line.get("discount_percent"):
											margin_type = "Percentage"
										if line.get("discount"):
											margin_type = "Amount"

										d = {
											"item_code": item_code,
											"warehouse": md_doc.warehouse,
											"qty": md_doc.qty if md_doc.qty <= received_qty else received_qty,
											"received_qty": md_doc.qty if md_doc.qty <= received_qty else received_qty,
											"rate": line.get('rate'),
											"expense_account": md_doc.expense_account,
											"cost_center": md_doc.cost_center,
											"uom": md_doc.uom,
											"stock_Uom": md_doc.stock_uom,
											"material_demand": md_doc.parent,
											"material_demand_item": md_doc.name,
											"margin_type": margin_type,
											"discount_percentage": line.get("discount_percent"),
											"discount_amount": line.get("discount"),
										}
										received_qty -= md_doc.qty

										key = (md_doc.warehouse)
										item_details.setdefault(key, {"details": []})
										fifo_queue = item_details[key]["details"]
										fifo_queue.append(d)
						else:
							if self.ignore_un_order_item:
								pass
							else:
								frappe.throw(_("Item <b>{0}</b> not found in Material Demand").format(item_code))

						if line.get('bonus'):
							bonus_un_odr.append(frappe._dict({
								"item_code": item_code,
								"warehouse": self.c_b_warehouse,
								"qty": line.get('bonus'),
								"is_free_item": 1,
								"rate": line.get('rate'),
								"discount_percentage": line.get("discount_percent"),
								"discount_amount": line.get("discount"),
								"uom": "Pack",
								"stock_Uom": "Nos",
							}))

					if item_details:
						if item_details:
							for key in item_details.keys():
								try:
									is_franchise = frappe.get_value("Warehouse", {'name': key}, "is_franchise")
									cost_center = frappe.get_value("Warehouse", {'name': key}, "cost_center")
									pi = frappe.new_doc("Purchase Receipt")
									pi.supplier = self.supplier
									pi.posting_date = nowdate()
									pi.due_date = nowdate()
									pi.cost_center = cost_center
									pi.company = self.company
									pi.purchase_invoice_creation_tool = self.name
									pi.purchase_request = self.purchase_request
									pi.update_stock = 1 if not is_franchise else 0
									pi.set_warehouse = key
									for d in item_details[key]['details']:
										pi.append("items", d)
									if pi.get('items'):
										pi.set_missing_values()
										pi.insert(ignore_permissions=True)
										count = 1
								except:
									continue
				if len(bonus_un_odr) > 0:
					pi = frappe.new_doc("Purchase Receipt")
					pi.supplier = self.supplier
					pi.posting_date = nowdate()
					pi.due_date = nowdate()
					pi.company = self.company
					pi.purchase_invoice_creation_tool = self.name
					pi.purchase_request = self.purchase_request
					pi.update_stock = 1
					for b in bonus_un_odr:
						margin_type = None
						if b.discount_percent:
							margin_type = "Percentage"
						if b.discount:
							margin_type = "Amount"
						item_doc = frappe.get_doc("Item",b.item_code)
						s = {
							"item_code": b.item_code,
							"warehouse": b.warehouse,
							"qty": b.qty,
							"received_qty": b.qty,
							"rate": b.rate if not b.is_free_item else 0,
							"is_free_item": b.is_free_item,
							"uom": b.uom,
							"stock_Uom": item_doc.stock_uom,
							"margin_type": margin_type,
							"discount_percentage": b.discount_percent,
							"discount_amount": b.discount
						}
						if b.is_free_item:
							s['price_list_rate'] = 0
						pi.append("items", s)
					pi.set_missing_values()
					pi.insert(ignore_permissions=True)
					count = 1
				if count:
					self.status = 'Receipt Created'
					self.db_update()
				return True

	@frappe.whitelist()
	def set_column_mapping(self):
		if self.supplier:
			map_col = frappe.get_value("File Column Mapping",{'supplier': self.supplier}, 'name')
			if map_col:
				map_col_doc = frappe.get_doc("File Column Mapping",map_col)
				column_to_field_map = {}
				for res in map_col_doc.field_mapping:
					col_pos = int(res.column_position) - 1
					if col_pos >= 0:
						if res.map_field != "Don't Import":
							column_to_field_map[str(col_pos)] = str(scrub(res.map_field))
						else:
							column_to_field_map[str(col_pos)] = scrub(res.map_field)
				column_dict = {"column_to_field_map": column_to_field_map}
				return column_dict


	@frappe.whitelist()
	def create_order_receiving(self):
		if self:
			doc = frappe.new_doc("Order Receiving")
			doc.status = 'Draft'
			doc.posting_date = self.date
			doc.company = self.company
			doc.c_b_warehouse = self.c_b_warehouse
			doc.purchase_request = self.purchase_request
			doc.supplier = self.supplier
			doc.ignore_un_order_item = self.ignore_un_order_item
			doc.warehouse = self.warehouse
			doc.purchase_invoice_creation_tool = self.name
			i = Importer(self.reference_doctype, data_import=self)
			data = i.import_file.get_payloads_for_import()
			if len(data) > 0:
				for d in data:
					line = d.get('doc')
					if line.get('qty') > 0:
						item = None
						item_code = None
						if line.get('item_code'):
							item = frappe.get_doc("Item", line.get('item_code'))
							item_code = item.name
						else:
							item = frappe.get_doc("Item Supplier", {'supplier_part_no': line.get('supplier_item_code'),
																	'supplier': self.supplier})
							item_code = item.parent
						item_doc = frappe.get_doc("Item", item_code)
						doc.append("items", {
							"item_code": item_code,
							"item_name": item_doc.item_name,
							"qty": line.get('qty'),
							"rate": line.get('rate'),
							"uom": 'Pack',
							"stock_uom": item_doc.stock_uom,
							"discount_percent": line.get("discount_percent") or 0 ,
							"discount": line.get("discount") or 0
						})
			doc.set_missing_value()
			return doc.as_dict()


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