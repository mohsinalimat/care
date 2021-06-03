
import frappe
from frappe.utils import flt, getdate
from frappe.model.mapper import map_doc, map_child_doc
from erpnext.accounts.doctype.pos_invoice_merge_log.pos_invoice_merge_log import POSInvoiceMergeLog, update_item_wise_tax_detail


class OverridePOSInvoiceMergeLog(POSInvoiceMergeLog):
    def validate(self):
        self.validate_pos_invoice_status()
        self.validate_pos_invoice_status()

    def process_merging_into_sales_invoice(self, data):
        sales_invoice = self.get_new_sales_invoice()

        sales_invoice = self.merge_pos_invoice_into(sales_invoice, data)

        sales_invoice.is_consolidated = 1
        sales_invoice.set_posting_time = 1
        sales_invoice.posting_date = getdate(self.posting_date)
        sales_invoice.save()
        submit_sales_invoice(sales_invoice)
        self.consolidated_invoice = sales_invoice.name

        return sales_invoice.name

    def process_merging_into_credit_note(self, data):
        credit_note = self.get_new_sales_invoice()
        credit_note.is_return = 1

        credit_note = self.merge_pos_invoice_into(credit_note, data)

        credit_note.is_consolidated = 1
        credit_note.set_posting_time = 1
        credit_note.posting_date = getdate(self.posting_date)
        # TODO: return could be against multiple sales invoice which could also have been consolidated?
        # credit_note.return_against = self.consolidated_invoice
        credit_note.save()
        submit_sales_invoice(credit_note)

        self.consolidated_credit_note = credit_note.name

        return credit_note.name

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


def submit_sales_invoice(sales_invoice):
    lst = []
    for line in sales_invoice.items:
        data_dict = {'item_code': line.item_code, 'warehouse': line.warehouse,
                     'posting_date': sales_invoice.posting_date, 'posting_time': sales_invoice.posting_time,
                     'voucher_type': 'Sales Invoice', 'voucher_no': sales_invoice.name, 'time_format': '%H:%i:%s'}
        previous_sle = get_previous_sle_of_current_voucher(data_dict)
        qty_after_transaction = 0
        if previous_sle:
            qty_after_transaction = previous_sle.qty_after_transaction

        diff = qty_after_transaction - line.qty
        if diff < 0 and abs(diff) > 0.0001:
            lst.append(1)
        else:
            lst.append(0)
    if 1 not in lst:
        sales_invoice.submit()


def get_previous_sle_of_current_voucher(args):
    """get stock ledger entries filtered by specific posting datetime conditions"""

    args['time_format'] = '%H:%i:%s'
    if not args.get("posting_date"):
        args["posting_date"] = "1900-01-01"
    if not args.get("posting_time"):
        args["posting_time"] = "00:00"

    sle = frappe.db.sql("""
        select *, timestamp(posting_date, posting_time) as "timestamp"
        from `tabStock Ledger Entry`
        where item_code = %(item_code)s
            and warehouse = %(warehouse)s
            and is_cancelled = 0
            and timestamp(posting_date, time_format(posting_time, %(time_format)s)) < timestamp(%(posting_date)s, time_format(%(posting_time)s, %(time_format)s))
        order by timestamp(posting_date, posting_time) desc, creation desc
        limit 1""", args, as_dict=1)

    return sle[0] if sle else frappe._dict()

