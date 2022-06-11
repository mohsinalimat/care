# Copyright (c) 2022, RF and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now_datetime
from frappe.model.document import Document
import json
import requests

class Franchise(Document):
	@frappe.whitelist()
	def sync_data_on_franchise(self):
		print("-----------------------------------")
		self.set_account()
		self.set_item_group()
		self.set_item_brand()
		self.set_item_uom()
		self.set_manufacturer()
		self.set_supplier_group()
		self.set_supplier()
		self.set_item()
		self.set_item_price()
		self.set_pricing_rule()
		for res in self.franchise_list:
			if res.enable:
				res.last_update = now_datetime()
		self.save(ignore_permissions=True)

	def set_account(self):
		if self.franchise_list:
			for res in self.franchise_list:
				if res.enable:
					accounts_detail = frappe.db.sql("""select 'Account' as doctype, account_name, 
												account_currency, account_number, account_type, parent_account ,
												root_type, report_type, is_group, freeze_account, 
												balance_must_be, disabled,
												0 as by_pass_autoname from `tabAccount` 
												where modified >= '{0}' 
												order by lft,rgt""".format(res.last_update), as_dict=True)
					if accounts_detail:
						try:
							url = str(res.url) + "/api/method/care.utils.api.set_account"
							api_key = res.api_key
							api_secret = res.api_secret
							headers = {
								'Authorization': 'token ' + str(api_key) + ':' + str(api_secret)
							}
							datas = {
								"accounts": json.dumps(accounts_detail),
							}
							response = requests.post(url=url, headers=headers, params=datas)
							if response.status_code != 200:
								frappe.log_error(title="Account upload API Error", message=response.json())
								frappe.msgprint("Account API Error Log Generated", indicator='red', alert=True)
						except Exception as e:
							frappe.log_error(title="Account upload API Error", message=e)
							frappe.msgprint("Account API Error Log Generated", indicator='red', alert=True)

	def set_item_group(self):
		for res in self.franchise_list:
			if res.enable:
				groups = frappe.db.sql("""select 'Item Group' as doctype, item_group_name, is_group, 
							parent_item_group from `tabItem Group` 
							where modified >= '{0}' 
							order by lft,rgt""".format(res.last_update), as_dict=True)
				if groups:
					try:
						url = str(res.url) + "/api/method/care.utils.api.set_item_group"
						api_key = res.api_key
						api_secret = res.api_secret
						headers = {
							'Authorization': 'token ' + str(api_key) + ':' + str(api_secret)
						}
						datas = {
							"groups": json.dumps(groups),
						}
						response = requests.post(url=url, headers=headers, params=datas)
						if response.status_code != 200:
							frappe.log_error(title="Item Group upload API Error", message=response.json())
							frappe.msgprint("Item Group API Error Log Generated", indicator='red', alert=True)
					except Exception as e:
						frappe.log_error(title="Item Group upload API Error", message=e)
						frappe.msgprint("Item Group API Error Log Generated", indicator='red', alert=True)

	def set_item_brand(self):
		for res in self.franchise_list:
			if res.enable:
				brands = frappe.db.sql("""select 'Brand' as doctype, brand from `tabBrand` 
					where modified >= '{0}'""".format(res.last_update), as_dict=True)
				if brands:
					try:
						url = str(res.url) + "/api/method/care.utils.api.set_item_brand"
						api_key = res.api_key
						api_secret = res.api_secret
						headers = {
							'Authorization': 'token ' + str(api_key) + ':' + str(api_secret)
						}
						datas = {
							"brands": json.dumps(brands),
						}
						response = requests.post(url=url, headers=headers, params=datas)
						if response.status_code != 200:
							frappe.log_error(title="Brand upload API Error", message=response.json())
							frappe.msgprint("Brand API Error Log Generated", indicator='red', alert=True)
					except Exception as e:
						frappe.log_error(title="Brand upload API Error", message=e)
						frappe.msgprint("Brand API Error Log Generated", indicator='red', alert=True)

	def set_item_uom(self):
		for res in self.franchise_list:
			if res.enable:
				uoms = frappe.db.sql("""select 'UOM' as doctype, uom_name,must_be_whole_number,enabled 
						from `tabUOM` 
						where modified >= '{0}'""".format(res.last_update), as_dict=True)
				if uoms:
					try:
						url = str(res.url) + "/api/method/care.utils.api.set_item_uom"
						api_key = res.api_key
						api_secret = res.api_secret
						headers = {
							'Authorization': 'token ' + str(api_key) + ':' + str(api_secret)
						}
						datas = {
							"uoms": json.dumps(uoms),
						}
						response = requests.post(url=url, headers=headers, params=datas)
						if response.status_code != 200:
							frappe.log_error(title="UOM upload API Error", message=response.json())
							frappe.msgprint("UOM API Error Log Generated", indicator='red', alert=True)
					except Exception as e:
						frappe.log_error(title="UOM upload API Error", message=e)
						frappe.msgprint("UOM API Error Log Generated", indicator='red', alert=True)

	def set_manufacturer(self):
		for res in self.franchise_list:
			if res.enable:
				manufacturer = frappe.db.sql("""select 'Manufacturer' as doctype,short_name,full_name,website,country 
					from `tabManufacturer` where modified >= '{0}'""".format(res.last_update), as_dict=True)
				if manufacturer:
					try:
						url = str(res.url) + "/api/method/care.utils.api.set_manufacturer"
						api_key = res.api_key
						api_secret = res.api_secret
						headers = {
							'Authorization': 'token ' + str(api_key) + ':' + str(api_secret)
						}
						datas = {
							"manufacturers": json.dumps(manufacturer),
						}
						response = requests.post(url=url, headers=headers, params=datas)
						if response.status_code != 200:
							frappe.log_error(title="Manufacturer upload API Error", message=response.json())
							frappe.msgprint("Manufacturer API Error Log Generated", indicator='red', alert=True)
					except Exception as e:
						frappe.log_error(title="Manufacturer upload API Error", message=e)
						frappe.msgprint("Manufacturer API Error Log Generated", indicator='red', alert=True)

	def set_supplier_group(self):
		for res in self.franchise_list:
			if res.enable:
				supp_group = frappe.db.sql("""select 'Supplier Group' as doctype, supplier_group_name,parent_supplier_group,
							is_group from `tabSupplier Group` 
							where modified >= '{0}'
							order by lft,rgt""".format(res.last_update), as_dict=True)
				if supp_group:
					try:
						url = str(res.url) + "/api/method/care.utils.api.set_supplier_group"
						api_key = res.api_key
						api_secret = res.api_secret
						headers = {
							'Authorization': 'token ' + str(api_key) + ':' + str(api_secret)
						}
						datas = {
							"supp_groups": json.dumps(supp_group),
						}
						response = requests.post(url=url, headers=headers, params=datas)
						if response.status_code != 200:
							frappe.log_error(title="Supplier Group upload API Error", message=response.json())
							frappe.msgprint("Supplier Group API Error Log Generated", indicator='red', alert=True)
					except Exception as e:
						frappe.log_error(title="Supplier Group upload API Error", message=e)
						frappe.msgprint("Supplier Group API Error Log Generated", indicator='red', alert=True)

	def set_supplier(self):
		for res in self.franchise_list:
			if res.enable:
				suppliers = frappe.db.sql("""select 'Supplier' as doctype, name, supplier_name, supplier_group, country, 
							supplier_type from `tabSupplier` 
							where modified >= '{0}' 
							order by creation""".format(res.last_update), as_dict=True)
				if suppliers:
					try:
						url = str(res.url) + "/api/method/care.utils.api.set_supplier"
						api_key = res.api_key
						api_secret = res.api_secret
						headers = {
							'Authorization': 'token ' + str(api_key) + ':' + str(api_secret)
						}
						datas = {
							"suppliers": json.dumps(suppliers),
						}
						response = requests.post(url=url, headers=headers, params=datas)
						if response.status_code != 200:
							frappe.log_error(title="Supplier upload API Error", message=response.json())
							frappe.msgprint("Supplier API Error Log Generated", indicator='red', alert=True)
					except Exception as e:
						frappe.log_error(title="Supplier upload API Error", message=e)
						frappe.msgprint("Supplier API Error Log Generated", indicator='red', alert=True)

	def set_item(self):
		for res in self.franchise_list:
			if res.enable:
				items = frappe.db.sql("""select name, item_name from `tabItem` where modified >= '{0}' 
							order by creation""".format(res.last_update), as_dict=True)
				if items:
					item_lst = []
					for itm in items:
						itm_doc = frappe.get_doc("Item", itm.name)
						item_dict = _get_item_dict(itm_doc, res.company_name)
						item_lst.append(item_dict)
					try:
						url = str(res.url) + "/api/method/care.utils.api.set_item"
						api_key = res.api_key
						api_secret = res.api_secret
						headers = {
							'Authorization': 'token ' + str(api_key) + ':' + str(api_secret)
						}
						datas = {
							"items": json.dumps(item_lst),
						}
						response = requests.post(url=url, headers=headers, params=datas)
						if response.status_code != 200:
							frappe.log_error(title="Item API Error", message=response.json())
							frappe.msgprint("Item API Error Log Generated", indicator='red', alert=True)
					except Exception as e:
						frappe.log_error(title="Item upload API Error", message=e)
						frappe.msgprint("Item API Error Log Generated", indicator='red', alert=True)

	def set_item_price(self):
		for res in self.franchise_list:
			if res.enable and res.update_price:
				item_prices = frappe.db.sql("""select 'Item Price' as doctype, item_code, item_name, item_description, 
								buying, selling, price_list, 
								CONVERT(valid_from, CHAR) as valid_from, currency,packing_unit, uom, 
								price_list_rate from `tabItem Price` where modified >= '{0}'""".format(res.last_update), as_dict=True)
				if item_prices:
					try:
						url = str(res.url) + "/api/method/care.utils.api.set_item_price"
						api_key = res.api_key
						api_secret = res.api_secret
						headers = {
							'Authorization': 'token ' + str(api_key) + ':' + str(api_secret)
						}
						datas = {
							"item_prices": json.dumps(item_prices)
						}
						response = requests.post(url=url, headers=headers, params=datas)
						if response.status_code != 200:
							frappe.log_error(title="Item Price upload API Error", message=response.json())
							frappe.msgprint("Item Price API Error Log Generated", indicator='red', alert=True)
					except Exception as e:
						frappe.log_error(title="Item Price upload API Error", message=e)
						frappe.msgprint("Item Price API Error Log Generated", indicator='red', alert=True)

	def set_pricing_rule(self):
		for res in self.franchise_list:
			if res.enable and res.update_price:
				rules = frappe.db.sql("""select name from `tabPricing Rule` where modified >= '{0}' 
							order by creation""".format(res.last_update), as_dict=True)
				if rules:
					rule_lst = []
					for itm in rules:
						itm_doc = frappe.get_doc("Pricing Rule", itm.name).as_dict()
						for key in ['name', 'creation', 'modified','company', 'modified_by', 'owner','warehouse', 'docstatus', 'parent', 'parentfield', 'parenttype', 'idx', 'naming_series']:
							itm_doc.pop(key)
						items = []
						for itm in itm_doc.get('items'):
							items.append({
								"item_code": itm.item_code,
								"uom": itm.uom
							})
						itm_doc['items'] = items
						if itm_doc.get('valid_from'):
							itm_doc['valid_from'] = str(itm_doc.get('valid_from'))
						if itm_doc.get('valid_upto'):
							itm_doc['valid_upto'] = str(itm_doc.get('valid_upto'))

						supplier_name = None
						if itm_doc.get('supplier'):
							supplier_name = frappe.get_value("Supplier", {'name': itm_doc.get('supplier')}, 'supplier_name')

						itm_doc['supplier_name'] = supplier_name
						rule_lst.append(itm_doc)
					try:
						url = str(res.url) + "/api/method/care.utils.api.set_price_rule"
						api_key = res.api_key
						api_secret = res.api_secret
						headers = {
							'Authorization': 'token ' + str(api_key) + ':' + str(api_secret)
						}
						datas = {
							"rules": json.dumps(rule_lst),
						}
						response = requests.post(url=url, headers=headers, params=datas)
						if response.status_code != 200:
							frappe.log_error(title="Pricing rule API Error", message=response.json())
							frappe.msgprint("Pricing rule API Error Log Generated", indicator='red', alert=True)
					except Exception as e:
						frappe.log_error(title="Pricing rule upload API Error", message=e)
						frappe.msgprint("Pricing rule API Error Log Generated", indicator='red', alert=True)


def _get_item_dict(itm_doc, company):
	item_dict = {
		"doctype": "Item",
		"item_code": itm_doc.name,
		"item_name": itm_doc.item_name,
		"stock_uom": itm_doc.stock_uom,
		"packing_name": itm_doc.packing_name,
		"disabled": itm_doc.disabled,
		"allow_alternative_item": itm_doc.allow_alternative_item,
		"is_stock_item": itm_doc.is_stock_item,
		"include_item_in_manufacturing": itm_doc.include_item_in_manufacturing,
		"over_delivery_receipt_allowance": itm_doc.over_delivery_receipt_allowance,
		"over_billing_allowance": itm_doc.over_billing_allowance,
		"non_returnable": itm_doc.non_returnable,
		"is_fridge_item": itm_doc.is_fridge_item,
		"is_narcotics": itm_doc.is_narcotics,
		"brand": itm_doc.brand,
		"description": itm_doc.description,
		"generic_name": itm_doc.generic_name,
		"item_group": itm_doc.item_group,
		"shelf_life_in_days": itm_doc.shelf_life_in_days,
		"end_of_life": str(itm_doc.end_of_life),
		"default_material_request_type": itm_doc.default_material_request_type,
		"valuation_method": itm_doc.valuation_method,
		"warranty_period": itm_doc.warranty_period,
		"weight_per_unit": itm_doc.weight_per_unit,
		"weight_uom": itm_doc.weight_uom,
		"has_batch_no": itm_doc.has_batch_no,
		"has_serial_no": itm_doc.has_serial_no,
		"serial_no_series": itm_doc.serial_no_series,
		"has_expiry_date": itm_doc.has_expiry_date,
		"retain_sample": itm_doc.retain_sample,
		"batch_number_series": itm_doc.batch_number_series,
		"is_purchase_item": itm_doc.is_purchase_item,
		"purchase_uom": itm_doc.purchase_uom,
		"lead_time_days": itm_doc.lead_time_days,
		"min_order_qty": itm_doc.min_order_qty,
		"safety_stock": itm_doc.safety_stock,
		"is_customer_provided_item": itm_doc.is_customer_provided_item,
		"manufacturer": itm_doc.manufacturer,
		"delivered_by_supplier": itm_doc.delivered_by_supplier,
		"is_sales_item": itm_doc.is_sales_item,
		"grant_commission": itm_doc.grant_commission,
		"max_discount": itm_doc.max_discount,
	}
	uoms = []
	for c in itm_doc.uoms:
		uoms.append({'uom': c.uom, 'conversion_factor': c.conversion_factor})
	if uoms:
		item_dict['uoms'] = uoms

	item_default = []
	for di in itm_doc.item_defaults:
		supplier_name = None
		if di.default_supplier:
			supplier_name = frappe.get_value("Supplier",{'name': di.default_supplier}, 'supplier_name')
		item_default.append({
			"company": company,
			"default_discount_account": di.default_discount_account,
			"default_supplier": di.default_supplier,
			"supplier_name": supplier_name,
			"expense_account": di.expense_account,
			"default_provisional_account": di.default_provisional_account,
			"income_account": di.income_account,
		})
	if item_default:
		item_dict['item_defaults'] = item_default
	return frappe._dict(item_dict)


def sync_data_scheduler():
	frappe.enqueue(upload_data, queue='long')

def upload_data():
	franchise = frappe.get_single("Franchise")
	franchise.sync_data_on_franchise()