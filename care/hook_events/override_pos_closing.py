from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import get_datetime, flt
from erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry import POSClosingEntry
from datetime import datetime
from frappe.utils import time_diff_in_hours
from erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry import get_pos_invoices
from erpnext.accounts.doctype.pos_invoice_merge_log.pos_invoice_merge_log import create_merge_logs
from erpnext.accounts.doctype.pos_invoice_merge_log.pos_invoice_merge_log import get_all_unconsolidated_invoices, enqueue_job, get_invoice_customer_map


@frappe.whitelist()
def execute_pos_invoices():
    make_closing_entry()
    pos_profiles = frappe.get_list("POS Profile", filters={"disabled": 0}, fields=["name"], order_by="creation")
    for res in pos_profiles:
        make_opening_entry(res.name)

def make_opening_entry(pos_profile,date_time=None):
    check_open_entry = frappe.db.sql("""select * from `tabPOS Opening Entry` where status = 'Open' and docstatus = 1 and pos_profile = %s and posting_date = %s""", (pos_profile,datetime.now().date()))
    if not check_open_entry:
        pos_profile_user = frappe.get_list("POS Profile User", filters={"default": 1, "parent": pos_profile}, fields=["user"], limit=1)[0].user
        profile_doc = frappe.get_doc("POS Profile", pos_profile)
        pos_o_entry = frappe.new_doc("POS Opening Entry")

        validate_open_entry_date_time = frappe.db.sql("""select * from `tabPOS Opening Entry` where docstatus = 1 and pos_profile  = %s and posting_date = %s""", (pos_profile, datetime.now().date()))
        if date_time:
            pos_o_entry.period_start_date = date_time
            pos_o_entry.posting_date = datetime.strptime(str(date_time), '%Y-%m-%d')

        elif not validate_open_entry_date_time:
            date_str = str(datetime.now().date()) + " 00:00:00"
            p_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            pos_o_entry.period_start_date = p_date
            pos_o_entry.posting_date = datetime.now().date()
        else:
            pos_o_entry.period_start_date = datetime.now()
            pos_o_entry.posting_date = datetime.now().date()

        pos_o_entry.user = pos_profile_user
        pos_o_entry.company = profile_doc.company
        pos_o_entry.pos_profile = pos_profile
        for account in profile_doc.payments:
            pos_o_entry.append("balance_details",{
                "mode_of_payment": account.mode_of_payment,
                "opening_amount": 0
            })
        pos_o_entry.insert(ignore_permissions=True)
        pos_o_entry.validate()
        pos_o_entry.submit()

def make_closing_entry():
    pos_opening_entries = frappe.get_list("POS Opening Entry", filters={"status": "Open", "docstatus": 1}, fields=["name"])
    enabled = frappe.db.get_single_value('POS Process Settings', 'enabled')
    execution_interval = 5 #set Interval
    if enabled:
        execution_interval = frappe.db.get_single_value('POS Process Settings', 'execution_interval')
    for open_e in pos_opening_entries:
        try:
            pos_o_entry = frappe.get_doc("POS Opening Entry", open_e.name)
            hours = time_diff_in_hours(datetime.now(), pos_o_entry.period_start_date)
            if hours >= execution_interval:
                pos_c_entry = frappe.new_doc("POS Closing Entry")
                if datetime.now().date() == pos_o_entry.posting_date:
                    pos_c_entry.period_end_date = datetime.now()
                    pos_c_entry.posting_date = datetime.now().date()
                else:
                    date_str = str(pos_o_entry.posting_date) + " 23:59:59"
                    p_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    pos_c_entry.period_end_date = p_date
                    pos_c_entry.posting_date = pos_o_entry.posting_date
                pos_c_entry.pos_opening_entry = pos_o_entry.name
                pos_c_entry.period_start_date = pos_o_entry.period_start_date
                pos_c_entry.pos_profile = pos_o_entry.pos_profile
                pos_c_entry.user = pos_o_entry.user
                pos_c_entry.company = pos_o_entry.company
                pos_line = get_pos_invoices(pos_c_entry.period_start_date, pos_c_entry.period_end_date, pos_c_entry.pos_profile, pos_c_entry.user)
                grand_total = net_total = total_quantity = 0

                payment_dict = {}
                for res in pos_o_entry.balance_details:
                    payment_dict[res.mode_of_payment] = 0
                invoice_lst = []
                for res in pos_line:
                    if res.name not in invoice_lst:
                        invoice_lst.append(res.name)
                    pos_c_entry.append("pos_transactions",{
                        "pos_invoice": res.name,
                        "posting_date": res.posting_date,
                        "grand_total": res.grand_total,
                        "customer": res.customer
                    })
                    grand_total += flt(res.grand_total)
                    net_total += flt(res.net_total)
                    total_quantity += flt(res.total_qty)
                pos_c_entry.grand_total = grand_total
                pos_c_entry.net_total = net_total
                pos_c_entry.total_quantity = total_quantity
                result = None
                if invoice_lst:
                    query = ""
                    if len(invoice_lst) == 1:
                        query = "select mode_of_payment,sum(base_amount) as total from `tabSales Invoice Payment` where parent = '{0}' ".format(invoice_lst[0])
                    else:
                        query = "select mode_of_payment,sum(base_amount) as total from `tabSales Invoice Payment` where parent in {0} ".format(tuple(invoice_lst))
                    result = frappe.db.sql(query, as_dict=True)

                if result:
                    for res in payment_dict.keys():
                        for r in result:
                            if res == r.mode_of_payment:
                                payment_dict[res] += r.total

                for res in payment_dict.keys():
                    pos_c_entry.append("payment_reconciliation",{
                        'mode_of_payment': res,
                        'opening_amount': 0,
                        'expected_amount': flt(payment_dict[res]),
                        'closing_amount': 0
                    })
                pos_c_entry.as_dict()
                if pos_c_entry.pos_transactions:
                    pos_c_entry.insert(ignore_permissions=True)
                    pos_c_entry.validate()
                    pos_c_entry.flags.ignore_validate_update_after_submit = True
                    pos_c_entry.submit()
                    make_opening_entry(pos_c_entry.pos_profile, pos_c_entry.period_end_date)
        except Exception as e:
            print("-----------e",e)
            pass


def consolidate_pos_invoices(pos_invoices=None, closing_entry=None):
    invoices = pos_invoices or (closing_entry and closing_entry.get('pos_transactions')) or get_all_unconsolidated_invoices()
    invoice_by_customer = get_invoice_customer_maps(invoices,closing_entry)
    if len(invoices) >= 10 and closing_entry:
        closing_entry.set_status(update=True, status='Queued')
        enqueue_job(create_merge_logs, invoice_by_customer=invoice_by_customer, closing_entry=closing_entry)
    else:
        create_merge_logs(invoice_by_customer, closing_entry)

def get_invoice_customer_maps(invoices, closing_entry=None):
    pos_profile = frappe.get_doc("POS Profile", closing_entry.pos_profile)
    pos_invoice_customer_map = {}
    if pos_profile.customer:
        for inv in invoices:
            check_payment = frappe.get_list("Sales Invoice Payment", filters={"parent": inv.pos_invoice, "mode_of_payment":['in', ['CitiLedger', 'MAP']]}, fields=["name"])
            if check_payment:
                customer = inv.get('customer')
                pos_invoice_customer_map.setdefault(customer, [])
                pos_invoice_customer_map[customer].append(inv)
            else:
                pos_invoice_customer_map.setdefault(pos_profile.customer, [])
                pos_invoice_customer_map[pos_profile.customer].append(inv)
        return pos_invoice_customer_map

    else:
        return get_invoice_customer_map(invoices)


@frappe.whitelist()
def get_pos_invoices(start, end, pos_profile, user):
    data = frappe.db.sql("""
    select
        name, timestamp(posting_date, posting_time) as "timestamp"
    from
        `tabPOS Invoice`
    where docstatus = 1 and pos_profile = %s and ifnull(consolidated_invoice,'') = ''
    """, (pos_profile), as_dict=1)
    # print("-------------",pos_profile,start,end)
    data = list(filter(lambda d: get_datetime(start) <= get_datetime(d.timestamp) <= get_datetime(end), data))
    # need to get taxes and payments so can't avoid get_doc
    data = [frappe.get_doc("POS Invoice", d.name).as_dict() for d in data]

    return data

class OverridePOSClosingEntry(POSClosingEntry):
    def on_submit(self):
        consolidate_pos_invoices(closing_entry=self)

    def validate(self):
        if frappe.db.get_value("POS Opening Entry", self.pos_opening_entry, "status") != "Open":
            frappe.throw(_("Selected POS Opening Entry should be open."), title=_("Invalid Opening Entry"))


