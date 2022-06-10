import frappe
from frappe import _
from frappe.utils import flt, cint
from erpnext.accounts.doctype.gl_entry.gl_entry import GLEntry

class OverrideGLEntry(GLEntry):
	def check_mandatory(self):
		mandatory = ["account", "voucher_type", "voucher_no", "company"]
		for k in mandatory:
			if not self.get(k):
				frappe.throw(_("{0} is required").format(_(self.meta.get_label(k))))

		if not self.voucher_type in ('Purchase Invoice', 'Payment Entry'):
			if not (self.party_type and self.party):
				account_type = frappe.get_cached_value("Account", self.account, "account_type")
				if account_type == "Receivable":
					frappe.throw(
						_("{0} {1}: Customer is required against Receivable account {2}").format(
							self.voucher_type, self.voucher_no, self.account
						)
					)
				elif account_type == "Payable":
					frappe.throw(
						_("{0} {1}: Supplier is required against Payable account {2}").format(
							self.voucher_type, self.voucher_no, self.account
						)
					)

		# Zero value transaction is not allowed
		if not (flt(self.debit, self.precision("debit")) or flt(self.credit, self.precision("credit"))):
			frappe.throw(
				_("{0} {1}: Either debit or credit amount is required for {2}").format(
					self.voucher_type, self.voucher_no, self.account
				)
			)