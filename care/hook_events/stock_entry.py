import frappe
from frappe.utils import nowdate
from erpnext.accounts.party import get_party_account

def make_journal_entry(doc, method):
    if doc.is_material_return and doc.supplier:
        supplier_account = get_party_account('Supplier', doc.supplier, doc.company)

        lines = frappe.db.sql("""select expense_account, sum(amount) as amt 
                    from `tabStock Entry Detail` 
                    where parent = %s 
                    group by expense_account""", (doc.name), as_dict=True)
        total = 0
        jv = frappe.new_doc('Journal Entry')
        jv.voucher_type = 'Debit Note'
        jv.naming_series = 'JV-'
        jv.posting_date = nowdate()
        jv.company = doc.company
        jv.stock_entry = doc.name
        for res in lines:
            total += res.amt
            jv.append('accounts', {
                'account': res.expense_account,
                'credit_in_account_currency': res.amt,
                'is_advance': 'No'
            })
        jv.append('accounts', {
            'account': supplier_account,
            'party_type': 'Supplier',
            'party': doc.supplier,
            'debit_in_account_currency': total,
            'is_advance': 'No',
        })
        jv.save(ignore_permissions=True)
        # jv.submit()