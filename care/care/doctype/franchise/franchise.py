# Copyright (c) 2022, RF and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json
import requests

class Franchise(Document):
	@frappe.whitelist()
	def sync_data_on_franchise(self):
		self.set_account()
		self.set_item_group()
		self.set_item_brand()
		self.set_item_uom()
		self.set_manufacturer()
		self.set_supplier_group()
		self.set_supplier()

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