
import frappe
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from care.hook_events.util import round_amount_by_2p5_diff

class OverrideSalesInvoice(SalesInvoice):
    def validate(self):
        if self.docstatus == 1:
            self.discount_amount = round_amount_by_2p5_diff(self.grand_total)
        super(OverrideSalesInvoice, self).validate()