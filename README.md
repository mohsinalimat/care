## Care

Auto perform pos invoice

#### License

MIT

Core Changes for this App

## Gross Profit Report Bug. erpnext/erpnext/accounts/report/gross_profit/gross_profit.py  (564)
return (abs(previous_stock_value - flt(sle.stock_value))) * flt(row.qty) / abs(flt(sle.qty))

_______________________________________<br>
<b>Status Updater Issue</b>
Path: apps/erpnext/erpnext/controllers/status_updater.py<br>
Line: :233<br>
Comment the code.<br>
#if hasattr(d, "qty") and d.qty > 0 and self.get("is_return"):<br>
#frappe.throw(_("For an item {0}, quantity must be negative number").format(d.item_code))

