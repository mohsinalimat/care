import frappe

@frappe.whitelist()
def round_amount_by_2p5_diff(amount=0.0):
    a = round(float(amount), 2)
    x = str(a).split(".")
    amt = float(x[0][-1]) + (float(x[1]) / 100)
    round_amt = 0
    if 0 < amt < 5:
        if amt >= 2.5:
            round_amt = 5.00 - amt
            round_amt = 0 - round_amt
        else:
            round_amt = amt
            
    elif 5 < amt < 10:
        if amt >= 7.5:
            round_amt = 10 - amt
            round_amt = 0 - round_amt
        else:
            round_amt = amt - 5
    return round_amt