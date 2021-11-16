import frappe

def set_out_grand_total(doc, method):
    if doc.references:
        grand_total = out_total = 0
        for res in doc.references:
            grand_total += res.total_amount
            out_total += res.outstanding_amount
        doc.grand_total = grand_total
        doc.total_outstanding = out_total