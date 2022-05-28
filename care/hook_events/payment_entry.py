import json

import frappe
from frappe import ValidationError, _, scrub, throw
from frappe.utils import cint, comma_or, flt, getdate, nowdate
from six import iteritems, string_types
import erpnext
from erpnext.accounts.utils import get_account_currency, get_held_invoices
from erpnext.controllers.accounts_controller import get_supplier_block_status
from erpnext.setup.utils import get_exchange_rate
from frappe.model.naming import make_autoname
from erpnext.accounts.doctype.payment_entry.payment_entry import (get_outstanding_on_journal_entry,
                                                                  split_invoices_based_on_payment_terms,
                                                                  get_orders_to_be_billed,
                                                                  get_negative_outstanding_invoices)
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry


class InvalidPaymentEntry(ValidationError):
    pass


class OverridePaymentEntry(PaymentEntry):
    def on_submit(self):
        super(OverridePaymentEntry, self).on_submit()
        if self.apply_tax_withholding_amount and self.tax_withholding_category:
            category = frappe.get_doc('Tax Withholding Category', self.tax_withholding_category)
            for res in category.accounts:
                gl = frappe.get_value("GL Entry",
                                    {"voucher_no": self.name, "voucher_type": 'Payment Entry',
                                    'account': res.account}, "name")
                if gl:
                    gl_doc = frappe.get_doc("GL Entry",gl)
                    gl_doc.party_type = self.party_type
                    gl_doc.party = self.party
                    gl_doc.db_update()


def set_out_grand_total(doc, method):
    if doc.references:
        grand_total = out_total = 0
        for res in doc.references:
            grand_total += res.total_amount
            out_total += res.outstanding_amount
        doc.grand_total = grand_total
        doc.total_outstanding = out_total


@frappe.whitelist()
def get_reference_details(reference_doctype, reference_name, party_account_currency):
    total_amount = outstanding_amount = exchange_rate = bill_no = None
    ref_doc = frappe.get_doc(reference_doctype, reference_name)
    company_currency = ref_doc.get("company_currency") or erpnext.get_company_currency(ref_doc.company)

    if reference_doctype == "Fees":
        total_amount = ref_doc.get("grand_total")
        exchange_rate = 1
        outstanding_amount = ref_doc.get("outstanding_amount")
    elif reference_doctype == "Donation":
        total_amount = ref_doc.get("amount")
        outstanding_amount = total_amount
        exchange_rate = 1
    elif reference_doctype == "Dunning":
        total_amount = ref_doc.get("dunning_amount")
        exchange_rate = 1
        outstanding_amount = ref_doc.get("dunning_amount")
    elif reference_doctype == "Journal Entry" and ref_doc.docstatus == 1:
        total_amount = ref_doc.get("total_amount")
        if ref_doc.multi_currency:
            exchange_rate = get_exchange_rate(party_account_currency, company_currency, ref_doc.posting_date)
        else:
            exchange_rate = 1
            outstanding_amount = get_outstanding_on_journal_entry(reference_name)
    elif reference_doctype != "Journal Entry":
        if ref_doc.doctype == "Expense Claim":
            total_amount = flt(ref_doc.total_sanctioned_amount) + flt(ref_doc.total_taxes_and_charges)
        elif ref_doc.doctype == "Employee Advance":
            total_amount = ref_doc.advance_amount
            exchange_rate = ref_doc.get("exchange_rate")
            if party_account_currency != ref_doc.currency:
                total_amount = flt(total_amount) * flt(exchange_rate)
        elif ref_doc.doctype == "Gratuity":
            total_amount = ref_doc.amount
        if not total_amount:
            if party_account_currency == company_currency:
                total_amount = ref_doc.base_grand_total
                exchange_rate = 1
            else:
                total_amount = ref_doc.grand_total
        if not exchange_rate:
            # Get the exchange rate from the original ref doc
            # or get it based on the posting date of the ref doc.
            exchange_rate = ref_doc.get("conversion_rate") or \
                            get_exchange_rate(party_account_currency, company_currency, ref_doc.posting_date)
        if reference_doctype in ("Sales Invoice", "Purchase Invoice"):
            if reference_doctype == "Purchase Invoice":
                draft_payment = float(frappe.db.sql("""select sum(allocated_amount) from `tabPayment Entry Reference` pr
                                    inner join `tabPayment Entry` p on p.name = pr.parent
                                    where p.docstatus = 0 
                                    and pr.reference_doctype = 'Purchase Invoice' 
                                    and pr.reference_name = '{0}' """.format(reference_name))[0][0] or 0)
                outstanding_amount = ref_doc.get("outstanding_amount") - draft_payment
                bill_no = ref_doc.get("bill_no")
            else:
                outstanding_amount = ref_doc.get("outstanding_amount")
                bill_no = ref_doc.get("bill_no")
        elif reference_doctype == "Expense Claim":
            outstanding_amount = flt(ref_doc.get("total_sanctioned_amount")) + flt(
                ref_doc.get("total_taxes_and_charges")) \
                                 - flt(ref_doc.get("total_amount_reimbursed")) - flt(
                ref_doc.get("total_advance_amount"))
        elif reference_doctype == "Employee Advance":
            outstanding_amount = (flt(ref_doc.advance_amount) - flt(ref_doc.paid_amount))
            if party_account_currency != ref_doc.currency:
                outstanding_amount = flt(outstanding_amount) * flt(exchange_rate)
                if party_account_currency == company_currency:
                    exchange_rate = 1
        elif reference_doctype == "Gratuity":
            outstanding_amount = ref_doc.amount - flt(ref_doc.paid_amount)
        else:
            outstanding_amount = flt(total_amount) - flt(ref_doc.advance_paid)
    else:
        # Get the exchange rate based on the posting date of the ref doc.
        exchange_rate = get_exchange_rate(party_account_currency,
                                          company_currency, ref_doc.posting_date)

    return frappe._dict({
        "due_date": ref_doc.get("due_date"),
        "total_amount": flt(total_amount),
        "outstanding_amount": flt(outstanding_amount),
        "exchange_rate": flt(exchange_rate),
        "bill_no": bill_no
    })


@frappe.whitelist()
def get_outstanding_reference_documents(args):
    if isinstance(args, string_types):
        args = json.loads(args)

    if args.get('party_type') == 'Member':
        return

    # confirm that Supplier is not blocked
    if args.get('party_type') == 'Supplier':
        supplier_status = get_supplier_block_status(args['party'])
        if supplier_status['on_hold']:
            if supplier_status['hold_type'] == 'All':
                return []
            elif supplier_status['hold_type'] == 'Payments':
                if not supplier_status['release_date'] or getdate(nowdate()) <= supplier_status['release_date']:
                    return []

    party_account_currency = get_account_currency(args.get("party_account"))
    company_currency = frappe.get_cached_value('Company', args.get("company"), "default_currency")

    # Get positive outstanding sales /purchase invoices/ Fees
    condition = ""
    if args.get("voucher_type") and args.get("voucher_no"):
        condition = " and voucher_type={0} and voucher_no={1}" \
            .format(frappe.db.escape(args["voucher_type"]), frappe.db.escape(args["voucher_no"]))

    # Add cost center condition
    if args.get("cost_center"):
        condition += " and cost_center='%s'" % args.get("cost_center")

    date_fields_dict = {
        'posting_date': ['from_posting_date', 'to_posting_date'],
        'due_date': ['from_due_date', 'to_due_date']
    }

    for fieldname, date_fields in date_fields_dict.items():
        if args.get(date_fields[0]) and args.get(date_fields[1]):
            condition += " and {0} between '{1}' and '{2}'".format(fieldname,
                                                                   args.get(date_fields[0]), args.get(date_fields[1]))

    if args.get("company"):
        condition += " and company = {0}".format(frappe.db.escape(args.get("company")))

    outstanding_invoices = get_outstanding_invoices(args.get("party_type"), args.get("party"),
                                                    args.get("party_account"), filters=args, condition=condition)

    outstanding_invoices = split_invoices_based_on_payment_terms(outstanding_invoices)

    for d in outstanding_invoices:
        d["exchange_rate"] = 1
        if party_account_currency != company_currency:
            if d.voucher_type in ("Sales Invoice", "Purchase Invoice", "Expense Claim"):
                d["exchange_rate"] = frappe.db.get_value(d.voucher_type, d.voucher_no, "conversion_rate")
            elif d.voucher_type == "Journal Entry":
                d["exchange_rate"] = get_exchange_rate(
                    party_account_currency, company_currency, d.posting_date
                )
        if d.voucher_type in ("Purchase Invoice"):
            d["bill_no"] = frappe.db.get_value(d.voucher_type, d.voucher_no, "bill_no")

    # Get all SO / PO which are not fully billed or aginst which full advance not paid
    orders_to_be_billed = []
    if (args.get("party_type") != "Student"):
        orders_to_be_billed = get_orders_to_be_billed(args.get("posting_date"), args.get("party_type"),
                                                      args.get("party"), args.get("company"), party_account_currency,
                                                      company_currency, filters=args)

    # Get negative outstanding sales /purchase invoices
    negative_outstanding_invoices = []
    if args.get("party_type") not in ["Student", "Employee"] and not args.get("voucher_no"):
        negative_outstanding_invoices = get_negative_outstanding_invoices(args.get("party_type"), args.get("party"),
                                                                          args.get("party_account"),
                                                                          party_account_currency, company_currency,
                                                                          condition=condition)

    data = negative_outstanding_invoices + outstanding_invoices + orders_to_be_billed

    if not data:
        frappe.msgprint(_("No outstanding invoices found for the {0} {1} which qualify the filters you have specified.")
                        .format(_(args.get("party_type")).lower(), frappe.bold(args.get("party"))))

    return data


def get_outstanding_invoices(party_type, party, account, condition=None, filters=None):
    outstanding_invoices = []
    precision = frappe.get_precision("Sales Invoice", "outstanding_amount") or 2

    if account:
        root_type, account_type = frappe.get_cached_value("Account", account, ["root_type", "account_type"])
        party_account_type = "Receivable" if root_type == "Asset" else "Payable"
        party_account_type = account_type or party_account_type
    else:
        party_account_type = erpnext.get_party_account_type(party_type)

    if party_account_type == 'Receivable':
        dr_or_cr = "debit_in_account_currency - credit_in_account_currency"
        payment_dr_or_cr = "credit_in_account_currency - debit_in_account_currency"
    else:
        dr_or_cr = "credit_in_account_currency - debit_in_account_currency"
        payment_dr_or_cr = "debit_in_account_currency - credit_in_account_currency"

    held_invoices = get_held_invoices(party_type, party)

    invoice_list = frappe.db.sql("""
        select
            voucher_no, voucher_type, posting_date, due_date,
            ifnull(sum({dr_or_cr}), 0) as invoice_amount,
            account_currency as currency
        from
            `tabGL Entry`
        where
            party_type = %(party_type)s and party = %(party)s
            and account = %(account)s and {dr_or_cr} > 0
            and is_cancelled=0
            {condition}
            and ((voucher_type = 'Journal Entry'
                    and (against_voucher = '' or against_voucher is null))
                or (voucher_type not in ('Journal Entry', 'Payment Entry')))
        group by voucher_type, voucher_no
        order by posting_date, name""".format(
        dr_or_cr=dr_or_cr,
        condition=condition or ""
    ), {
        "party_type": party_type,
        "party": party,
        "account": account,
    }, as_dict=True)

    payment_entries = frappe.db.sql("""
        select against_voucher_type, against_voucher,
            ifnull(sum({payment_dr_or_cr}), 0) as payment_amount
        from `tabGL Entry`
        where party_type = %(party_type)s and party = %(party)s
            and account = %(account)s
            and {payment_dr_or_cr} > 0
            and against_voucher is not null and against_voucher != ''
            and is_cancelled=0
        group by against_voucher_type, against_voucher
    """.format(payment_dr_or_cr=payment_dr_or_cr), {
        "party_type": party_type,
        "party": party,
        "account": account
    }, as_dict=True)

    pe_map = frappe._dict()
    for d in payment_entries:
        pe_map.setdefault((d.against_voucher_type, d.against_voucher), d.payment_amount)

    for d in invoice_list:
        payment_amount = pe_map.get((d.voucher_type, d.voucher_no), 0)
        outstanding_amount = flt(d.invoice_amount - payment_amount, precision)
        if outstanding_amount > 0.5 / (10 ** precision):
            if (filters and filters.get("outstanding_amt_greater_than") and
                    not (outstanding_amount >= filters.get("outstanding_amt_greater_than") and
                         outstanding_amount <= filters.get("outstanding_amt_less_than"))):
                continue

            if not d.voucher_type == "Purchase Invoice" or d.voucher_no not in held_invoices:
                if d.voucher_type == "Purchase Invoice":
                    draft_payment = float(frappe.db.sql("""select sum(allocated_amount) from `tabPayment Entry Reference` pr
                                            inner join `tabPayment Entry` p on p.name = pr.parent
                                            where p.docstatus = 0 
                                            and pr.reference_doctype = 'Purchase Invoice' 
                                            and pr.reference_name = '{0}' """.format(d.voucher_no))[0][0] or 0)
                    outstanding_amount = outstanding_amount - draft_payment

                outstanding_invoices.append(
                    frappe._dict({
                        'voucher_no': d.voucher_no,
                        'voucher_type': d.voucher_type,
                        'posting_date': d.posting_date,
                        'invoice_amount': flt(d.invoice_amount),
                        'payment_amount': payment_amount,
                        'outstanding_amount': outstanding_amount,
                        'due_date': d.due_date,
                        'currency': d.currency
                    })
                )

    outstanding_invoices = sorted(outstanding_invoices, key=lambda k: k['due_date'] or getdate(nowdate()))
    return outstanding_invoices


def create_custom_series(doc, method):
    if doc:
        series = "PE-.DD.-.MM.-.YY.-.###"
        name = make_autoname(series)
        doc.custom_series = name
        doc.db_update()

