# Copyright (c) 2021, RF and contributors
# For license information, please see license.txt

import json
import frappe
import requests
from frappe import _
from frappe.model.document import Document
from erpnext.stock.get_item_details import get_conversion_factor
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.setup.doctype.brand.brand import get_brand_defaults
from care.hook_events.make_xlsx_file import make_xlsx,make_xlsx_summary
from care.hook_events.purchase_invoice import get_price_list_rate_for
import math

class PurchaseRequest(Document):

	def on_cancel(self):
		self.status = "Cancelled"
		self.db_update()

	@frappe.whitelist()
	def get_warehouse(self):
		wr = frappe.get_list("Warehouse", filters={'is_group': 0, 'auto_select_in_purchase_request': 1}, fields='*', order_by='name')
		for wr_doc in wr:
			if wr_doc.is_franchise:
				f_w_data = frappe.get_value("Franchise Item", {'warehouse': wr_doc.name})
				if f_w_data:
					f_w_doc = frappe.get_doc("Franchise Item", f_w_data)
					wr_doc['order_per'] = f_w_doc.reorder_prec
		return wr

	@frappe.whitelist()
	def get_suppliers_name(self):
		if self.suppliers:
			s_name = ""
			for res in self.suppliers:
				s = frappe.get_doc("Supplier",res.supplier)
				s_name += s.supplier_name + '\n'
			return s_name

	@frappe.whitelist()
	def get_items(self):
		item_details = []
		if not self.suppliers:
			frappe.throw(_("Select suppliers"))
		if not self.warehouses:
			frappe.throw(_("Select Warehouses"))

		s_lst = ["axop123"]
		s_name_lst = ["axop123"]
		w_lst = ["axop123","axop123"]
		f_w_lst = []
		for res in self.suppliers:
			s_lst.append(res.supplier)
		for res in self.supplier_name.split("\n"):
			if res and res != '':
				s_name_lst.append(res)

		warehouse_dict = {}
		for res in self.warehouses:
			warehouse_dict[res.warehouse] = res.order_per
			wr_doc = frappe.get_doc("Warehouse", res.warehouse)
			if wr_doc.is_franchise:
				f_w_lst.append(res.warehouse)
			else:
				w_lst.append(res.warehouse)

			if wr_doc.is_group:
				child_wr = frappe.get_list("Warehouse", filters={'parent_warehouse': wr_doc.name}, fields='*')
				for r in child_wr:
					wr = frappe.get_doc("Warehouse", r.name)
					warehouse_dict[r.name] = res.order_per
					if wr.is_franchise:
						f_w_lst.append(r.name)
					else:
						w_lst.append(r.name)

		query = """select i.name as item_code,
				i.item_name,
				i.description,
				i.brand,
				idf.default_supplier,
				idf.supplier_name,
				ird.warehouse,
				ird.warehouse_reorder_level,
				ird.warehouse_reorder_qty,
				ird.optimum_level,
				b.actual_qty,
				i.stock_uom,
				i.last_purchase_rate,
				0 as conversion_factor,
				0.0 as order_qty,
				null as last_purchase_date
				from `tabItem` i 
				inner join `tabItem Default` idf on idf.parent = i.name
				inner  join `tabItem Reorder` ird on ird.parent = i.name
				left join `tabBin` b on b.item_code = i.name and b.warehouse = ird.warehouse
				where 
				idf.default_supplier is not null
				and ird.warehouse is not null
				and i.is_stock_item = 1 
				and i.has_variants = 0
				and i.disabled = 0
				and ird.warehouse_reorder_level > 0 
				and ird.warehouse_reorder_qty > 0 
				and ird.optimum_level > 0
				and (b.actual_qty < ird.warehouse_reorder_level or b.actual_qty is null)
				and idf.default_supplier in {0}""".format(tuple(s_lst))
		if w_lst:
			query += """ and ird.warehouse in {0}""".format(tuple(w_lst))
		query += " order by idf.default_supplier, ird.warehouse, i.name"
		item_details = frappe.db.sql(query,as_dict=True)
		for res in item_details:
			conversion_factor = 1
			conversion = get_conversion_factor(res.item_code, self.order_uom)
			if conversion:
				conversion_factor = conversion['conversion_factor']
			res['conversion_factor'] = conversion_factor
		if f_w_lst:
			franchise = frappe.get_single("Franchise")
			if franchise.is_enabled:
				for w in f_w_lst:
					f_w_data = frappe.get_value("Franchise Item", {'warehouse': w, 'enable': 1})
					if f_w_data:
						try:
							f_w_doc = frappe.get_doc("Franchise Item", f_w_data)
							if f_w_doc.url and f_w_doc.api_key and f_w_doc.api_secret:
								url = str(f_w_doc.url)+"/api/method/care.utils.api.get_franchise_order"
								api_key = f_w_doc.api_key
								api_secret = f_w_doc.api_secret
								headers = {
									'Authorization': 'token ' + str(api_key)+':' + str(api_secret)
								}
								datas = {
									"supplier": json.dumps(s_name_lst),
									"order_uom": 'Pack',
									"warehouse": w
								}
								response = requests.get(url=url, headers=headers, data=datas)
								if response.status_code == 200:
									response = frappe.parse_json(response.content.decode())
									data = response.message
									item_details.extend(data)
								else:
									frappe.log_error(title="Franchise API Error", message=response.json())
									frappe.msgprint("Error Log Generated", indicator='red', alert=True)
						except Exception as e:
							frappe.log_error(title="Franchise API Error", message=e)
							frappe.msgprint("Error Log Generated", indicator='red', alert=True)
							continue
		for d in item_details:
			supplier = frappe.get_value("Supplier",{"supplier_name": d.get('supplier_name')}, "name")
			d['default_supplier'] = supplier
			if d.get('warehouse') in warehouse_dict.keys():
				actual_qty = 0
				if d.get('actual_qty'):
					actual_qty = float(d.get('actual_qty'))
				order_qty = 0
				if self.base_on == "Reorder Quantity":
					if 0 <= actual_qty < float(d.get('warehouse_reorder_level')):
						total_qty = actual_qty + float(d.get('warehouse_reorder_qty'))
						if total_qty >= float(d.get('optimum_level')):
							order_qty = float(d.get('optimum_level')) - actual_qty
						else:
							order_qty = float(d.get('warehouse_reorder_qty'))

				if self.base_on == "Optimal Level":
					if 0 <= actual_qty < float(d.get('optimum_level')):
						total_qty = actual_qty + float(d.get('optimum_level'))
						if total_qty >= float(d.get('optimum_level')):
							order_qty = float(d.get('optimum_level')) - actual_qty
						else:
							order_qty = float(d.get('optimum_level'))

				percent = warehouse_dict[d.get('warehouse')]
				qty = order_qty * (percent / 100)
				d['order_qty'] = qty
				avl_stock_qty_corp = 0
				if frappe.db.exists("Warehouse", "Corporate Office Store - CP"):
					avl_qty = float(frappe.db.sql("""select IFNULL(sum(actual_qty), 0) from `tabBin`
								where item_code = %s and warehouse = 'Corporate Office Store - CP' """,
												  (d.get('item_code')))[0][0] or 0)
					avl_stock_qty_corp = math.floor(avl_qty / d.get('conversion_factor'))

				j_d = json.dumps({
							"item_code": d.get('item_code'),
							"price_list": frappe.defaults.get_defaults().buying_price_list,
							"currency": frappe.defaults.get_defaults().currency,
							"price_list_currency": frappe.defaults.get_defaults().currency,
							"supplier": d.get('default_supplier'),
							"uom": self.order_uom,
							"stock_uom": d.get('stock_uom'),
							"qty": d.get('order_qty'),
							"transaction_date": self.date,
							"doctype": self.doctype,
							"name": self.name,
							"conversion_factor": d.get('conversion_factor')
						})
				rate = get_price_list_rate_for(d.get('item_code'),j_d )
				d['last_purchase_rate'] = rate if rate else 0
				d["avl_stock_qty_corp"] = avl_stock_qty_corp

				last_purchase_date = frappe.db.sql("""select p.posting_date from `tabPurchase Receipt` as p
											inner join `tabPurchase Receipt Item` as pi on p.name = pi.parent 
											where pi.item_code = '{0}' 
											and p.docstatus = 1 
											order by p.posting_date desc limit 1""".format(d.get('item_code')))
				if last_purchase_date:
					d["last_purchase_date"] = last_purchase_date[0][0]

		return item_details

	def on_submit(self):
		if not self.items:
			frappe.throw(_("no Items Found. Please set first"))
		self.make_material_demand()
		# self.status = "Submitted"
		self.status = "Open"
		self.db_update()

	def make_material_demand(self):
		if self.items:
			item_details = {}
			for res in self.items:
				key = (res.supplier, res.warehouse)
				item_details.setdefault(key, {"details": []})
				fifo_queue = item_details[key]["details"]
				fifo_queue.append(res)
			if item_details:
				for key in item_details.keys():
					md = frappe.new_doc("Material Demand")
					md.supplier = key[0]
					md.warehouse = key[1]
					md.transaction_date = self.date
					md.schedule_date = self.required_by
					md.company = self.company
					md.purchase_request = self.name
					for d in item_details[key]['details']:
						conversion_factor = 1
						conversion = get_conversion_factor(d.item_code, self.order_uom)
						if conversion:
							conversion_factor = conversion['conversion_factor']

						item_defaults = get_item_defaults(d.item_code, self.company)
						item_group_defaults = get_item_group_defaults(d.item_code, self.company)
						brand_defaults = get_brand_defaults(d.item_code, self.company)
						expense_account = get_default_expense_account(item_defaults, item_group_defaults, brand_defaults)
						cost_center = get_default_cost_center(self,item_defaults, item_group_defaults, brand_defaults)

						# qty = math.ceil(d.order_qty / conversion_factor)
						md.append("items", {
							"item_code": d.item_code,
							"item_name": d.item_name,
							"brand": d.brand,
							"description": d.item_description,
							"schedule_date": self.required_by,
							"qty": d.pack_order_qty,
							"stock_uom": d.stock_uom,
							"uom": self.order_uom,
							"conversion_factor": conversion_factor,
							"warehouse": key[1],
							"actual_qty": d.avl_qty,
							"rate": d.rate,
							"amount": d.rate * d.pack_order_qty,
							"stock_qty": d.order_qty * conversion_factor,
							"expense_account": expense_account,
							"cost_center": cost_center
						})
					md.insert(ignore_permissions=True)
					if self.submit_md:
						md.submit()
			frappe.msgprint(_("Material Demand Created"), alert=True)

	@frappe.whitelist()
	def make_purchase_order(self):
		if self.items:
			item_details = {}
			for res in self.items:
				is_franchise = frappe.get_value("Warehouse", {'name': res.warehouse}, "is_franchise")
				key = ''
				if is_franchise:
					key = (res.supplier, res.warehouse)
				else:
					key = (res.supplier, "common")
				item_details.setdefault(key, {"details": []})
				fifo_queue = item_details[key]["details"]
				fifo_queue.append(res)

			if item_details:
				for key in item_details.keys():
					po = frappe.new_doc("Purchase Order")
					po.supplier = key[0]
					po.company = self.company
					po.transaction_date = self.date
					po.schedule_date = self.required_by
					po.purchase_request = self.name
					if frappe.db.exists('Warehouse', key[1]):
						po.set_warehouse = key[1]

					for d in item_details[key]['details']:
						item = frappe.get_doc("Item", d.item_code)
						po.append("items", {
							"item_code": d.item_code,
							"description": item.description,
							"brand": d.brand,
							"warehouse": d.warehouse,
							"qty": d.pack_order_qty,
							"rate": d.rate,
							"stock_uom": d.stock_uom,
							"uom": self.order_uom,
							"conversion_factor": d.conversion_factor,
							"allow_zero_valuation_rate": 0
						})
					po.set_missing_values()
					po.insert(ignore_permissions=True)
					if self.submit_pr:
						po.submit()

			self.status = "Order Created"
			self.db_update()



def get_default_expense_account(item, item_group, brand):
	return (item.get("expense_account")
		or item_group.get("expense_account")
		or brand.get("expense_account"))

def get_default_cost_center(args, item=None, item_group=None, brand=None, company=None):
	cost_center = None

	if not company and args.get("company"):
		company = args.get("company")

	if args.get('project'):
		cost_center = frappe.db.get_value("Project", args.get("project"), "cost_center", cache=True)

	if not cost_center and (item and item_group and brand):
		if args.get('customer'):
			cost_center = item.get('selling_cost_center') or item_group.get('selling_cost_center') or brand.get('selling_cost_center')
		else:
			cost_center = item.get('buying_cost_center') or item_group.get('buying_cost_center') or brand.get('buying_cost_center')

	elif not cost_center and args.get("item_code") and company:
		for method in ["get_item_defaults", "get_item_group_defaults", "get_brand_defaults"]:
			path = "erpnext.stock.get_item_details.{0}".format(method)
			data = frappe.get_attr(path)(args.get("item_code"), company)

			if data and (data.selling_cost_center or data.buying_cost_center):
				return data.selling_cost_center or data.buying_cost_center

	if not cost_center and args.get("cost_center"):
		cost_center = args.get("cost_center")

	if (company and cost_center
		and frappe.get_cached_value("Cost Center", cost_center, "company") != company):
		return None

	if not cost_center and company:
		cost_center = frappe.get_cached_value("Company",
			company, "cost_center")

	return cost_center

@frappe.whitelist()
def download_excel(purchase_request=None):
	if purchase_request:
		m_demands = frappe.db.sql("""select name  
					from `tabMaterial Demand` 
					where purchase_request ='{0}'""".format(purchase_request), as_list=True)
		lst = []
		for l in m_demands:
			lst.append(l[0])
		xlsx_file = make_xlsx(lst)
		frappe.response['filename'] = str(purchase_request) + '.xlsx'
		frappe.response['filecontent'] = xlsx_file.getvalue()
		frappe.response['type'] = 'binary'


@frappe.whitelist()
def download_excel_summary(purchase_request=None):
	if purchase_request:
		xlsx_file = make_xlsx_summary(purchase_request)
		frappe.response['filename'] = str(purchase_request) + '_summary.xlsx'
		frappe.response['filecontent'] = xlsx_file.getvalue()
		frappe.response['type'] = 'binary'


def pur_req_pdf_summary(doc):
	supp_lst = ['##efef']
	for res in doc.suppliers:
		supp_lst.append(res.supplier)
	data = frappe.db.sql("""select p1.item_code, p1.item_name, p1.brand, sum(p1.pack_order_qty) as pack_order_qty ,
	 	ifnull((select p2.supplier_part_no from `tabItem Supplier`as p2 where p2.parent = p1.item_code and supplier in {0} limit 1),"") as part_number
		from `tabPurchase Request Item` as p1
		where p1.parent = '{1}'
		group by p1.item_code, p1.item_name, p1.brand 
		order by p1.brand, p1.item_name """.format(tuple(supp_lst), doc.name), as_dict=True)
	return data


def update_status_as_open():
	frappe.db.sql("""UPDATE `tabPurchase Request` SET status = 'Open' 
				WHERE status = 'Submitted'""")