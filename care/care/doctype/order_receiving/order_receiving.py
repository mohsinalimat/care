# Copyright (c) 2021, RF and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import nowdate
from frappe.model.document import Document

class OrderReceiving(Document):

	def on_submit(self):
		self.make_purchase_invoice()

	def make_purchase_invoice(self):
		material_demand = frappe.get_list("Material Demand", {'supplier': self.supplier, 'purchase_request': self.purchase_request},['name'])
		m_list = []
		for res in material_demand:
			m_list.append(res.name)
		if self.items:
			if self.warehouse:
				pi = frappe.new_doc("Purchase Invoice")
				pi.supplier = self.supplier
				pi.posting_date = nowdate()
				pi.due_date = nowdate()
				pi.company = self.company
				pi.order_receiving = self.name
				pi.update_stock = 1
				for d in self.items:
					md_item = frappe.get_value("Material Demand Item", {'item_code': d.get('item_code'), 'parent': ['in', m_list], "warehouse": self.warehouse}, "name")
					if md_item:
						md_doc = frappe.get_doc("Material Demand Item", md_item)
						pi.append("items", {
							"item_code": d.get('item_code'),
							"warehouse": md_doc.warehouse,
							"qty": d.get('qty'),
							"received_qty": d.get('qty'),
							"rate": d.get('rate'),
							"expense_account": md_doc.expense_account,
							"cost_center": md_doc.cost_center,
							"uom": md_doc.uom,
							"stock_Uom": md_doc.stock_uom,
							"material_demand": md_doc.parent,
							"material_demand_item": md_doc.name,
						})

					else:
						if not self.ignore_un_order_item:
							frappe.throw(_("Item <b>{0}</b> not found in Material Demand").format(d.get('item_code')))
				if pi.get('items'):
					pi.set_missing_values()
					pi.insert(ignore_permissions=True)

			else:
				item_details = {}
				for d in self.items:
					md_item = frappe.get_list("Material Demand Item", {'item_code': d.get('item_code'), 'parent': ['in', m_list]}, ['name'])
					received_qty = d.get('qty')
					if md_item:
						for p_tm in md_item:
							if received_qty > 0:
								md_doc = frappe.get_doc("Material Demand Item", p_tm.name)
								if md_doc:
									d = {
										"item_code": d.get('item_code'),
										"warehouse": md_doc.warehouse,
										"qty": md_doc.qty if md_doc.qty <= received_qty else received_qty,
										"received_qty": md_doc.qty if md_doc.qty <= received_qty else received_qty,
										"rate": d.get('rate'),
										"expense_account": md_doc.expense_account,
										"cost_center": md_doc.cost_center,
										"uom": md_doc.uom,
										"stock_Uom": md_doc.stock_uom,
										"material_demand": md_doc.parent,
										"material_demand_item": md_doc.name,
									}
									received_qty -= md_doc.qty

									key = (md_doc.warehouse)
									item_details.setdefault(key, {"details": []})
									fifo_queue = item_details[key]["details"]
									fifo_queue.append(d)
					else:
						if not self.ignore_un_order_item:
							frappe.throw(_("Item <b>{0}</b> not found in Material Demand").format(d.get('item_code')))
				if item_details:
					if item_details:
						for key in item_details.keys():
							try:
								pi = frappe.new_doc("Purchase Invoice")
								pi.supplier = self.supplier
								pi.posting_date = nowdate()
								pi.due_date = nowdate()
								pi.company = self.company
								pi.order_receiving = self.name
								pi.update_stock = 1
								pi.set_warehouse = key
								for d in item_details[key]['details']:
									pi.append("items", d)
								if pi.get('items'):
									pi.set_missing_values()
									pi.insert(ignore_permissions=True)
							except:
								continue
			frappe.msgprint(_("Purchase Invoice Created"), alert=1)


