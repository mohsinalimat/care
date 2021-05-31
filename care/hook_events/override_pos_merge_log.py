
import frappe
from frappe import _
from frappe.model import default_fields
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate
from frappe.utils.background_jobs import enqueue
from frappe.model.mapper import map_doc, map_child_doc
from frappe.utils.scheduler import is_scheduler_inactive
from frappe.core.page.background_jobs.background_jobs import get_info
import json
import six
from erpnext.accounts.doctype.pos_invoice_merge_log.pos_invoice_merge_log import POSInvoiceMergeLog, update_item_wise_tax_detail


class OverridePOSInvoiceMergeLog(POSInvoiceMergeLog):
    def validate(self):
        self.validate_pos_invoice_status()
        self.validate_pos_invoice_status()

    def merge_pos_invoice_into(self, invoice, data):
        items, payments, taxes = [], [], []
        loyalty_amount_sum, loyalty_points_sum = 0, 0
        for doc in data:
            doc.customer = invoice.customer
            map_doc(doc, invoice, table_map={"doctype": invoice.doctype})

            if doc.redeem_loyalty_points:
                invoice.loyalty_redemption_account = doc.loyalty_redemption_account
                invoice.loyalty_redemption_cost_center = doc.loyalty_redemption_cost_center
                loyalty_points_sum += doc.loyalty_points
                loyalty_amount_sum += doc.loyalty_amount

            for item in doc.get('items'):
                found = False
                for i in items:
                    if (i.item_code == item.item_code and not i.serial_no and not i.batch_no and
                            i.uom == item.uom and i.net_rate == item.net_rate):
                        found = True
                        i.qty = i.qty + item.qty

                if not found:
                    item.rate = item.net_rate
                    item.price_list_rate = 0
                    si_item = map_child_doc(item, invoice, {"doctype": "Sales Invoice Item"})
                    items.append(si_item)

            for tax in doc.get('taxes'):
                found = False
                for t in taxes:
                    if t.account_head == tax.account_head and t.cost_center == tax.cost_center:
                        t.tax_amount = flt(t.tax_amount) + flt(tax.tax_amount_after_discount_amount)
                        t.base_tax_amount = flt(t.base_tax_amount) + flt(tax.base_tax_amount_after_discount_amount)
                        update_item_wise_tax_detail(t, tax)
                        found = True
                if not found:
                    tax.charge_type = 'Actual'
                    tax.included_in_print_rate = 0
                    tax.tax_amount = tax.tax_amount_after_discount_amount
                    tax.base_tax_amount = tax.base_tax_amount_after_discount_amount
                    tax.item_wise_tax_detail = tax.item_wise_tax_detail
                    taxes.append(tax)

            for payment in doc.get('payments'):
                found = False
                for pay in payments:
                    if pay.account == payment.account and pay.mode_of_payment == payment.mode_of_payment:
                        pay.amount = flt(pay.amount) + flt(payment.amount)
                        pay.base_amount = flt(pay.base_amount) + flt(payment.base_amount)
                        found = True
                if not found:
                    payments.append(payment)

        if loyalty_points_sum:
            invoice.redeem_loyalty_points = 1
            invoice.loyalty_points = loyalty_points_sum
            invoice.loyalty_amount = loyalty_amount_sum

        invoice.set('items', items)
        invoice.set('payments', payments)
        invoice.set('taxes', taxes)
        invoice.additional_discount_percentage = 0
        invoice.discount_amount = 0.0
        invoice.taxes_and_charges = None
        invoice.ignore_pricing_rule = 1

        return invoice
