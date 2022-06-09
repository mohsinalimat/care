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

	def set_account(self):
		if self.franchise_list:
			accounts_detail = frappe.db.sql("""select 'Account' as doctype, account_name, 
							account_currency, account_number, account_type, parent_account ,
							root_type, report_type, is_group, freeze_account, 
							balance_must_be, disabled,
							0 as by_pass_autoname from `tabAccount` order by lft,rgt""", as_dict=True)
			for res in self.franchise_list:
				if res.enable:
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
		groups = frappe.db.sql("""select 'Item Group' as doctype, item_group_name, is_group, 
			parent_item_group from `tabItem Group` order by lft,rgt""", as_dict=True)
		for res in self.franchise_list:
			if res.enable:
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