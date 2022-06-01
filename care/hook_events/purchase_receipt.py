
import frappe
import erpnext
from frappe.utils import flt
from erpnext.controllers.taxes_and_totals import get_itemised_tax_breakup_data
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import PurchaseReceipt
from erpnext.stock.get_item_details import get_item_details
force_item_fields = (
    "item_group",
    "brand",
    "stock_uom",
    "is_fixed_asset",
    "item_tax_rate",
    "pricing_rules",
    "weight_per_unit",
    "weight_uom",
    "total_weight",
)


class OverridePurchaseReceipt(PurchaseReceipt):
    def calculate_taxes_and_totals(self):
        from care.hook_events.taxes_and_total import calculate_taxes_and_totals
        calculate_taxes_and_totals(self)

        if self.doctype in (
                "Sales Order",
                "Delivery Note",
                "Sales Invoice",
                "POS Invoice",
        ):
            self.calculate_commission()
            self.calculate_contribution()

    def set_missing_item_details(self, for_validate=False):
        """set missing item values"""
        from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

        if hasattr(self, "items"):
            parent_dict = {}
            for fieldname in self.meta.get_valid_columns():
                parent_dict[fieldname] = self.get(fieldname)

            if self.doctype in ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice"]:
                document_type = "{} Item".format(self.doctype)
                parent_dict.update({"document_type": document_type})

            # party_name field used for customer in quotation
            if (
                    self.doctype == "Quotation"
                    and self.quotation_to == "Customer"
                    and parent_dict.get("party_name")
            ):
                parent_dict.update({"customer": parent_dict.get("party_name")})

            self.pricing_rules = []
            for item in self.get("items"):
                if item.get("item_code"):
                    args = parent_dict.copy()
                    args.update(item.as_dict())

                    args["doctype"] = self.doctype
                    args["name"] = self.name
                    args["child_docname"] = item.name
                    args["ignore_pricing_rule"] = (
                        self.ignore_pricing_rule if hasattr(self, "ignore_pricing_rule") else 0
                    )

                    if not args.get("transaction_date"):
                        args["transaction_date"] = args.get("posting_date")

                    if self.get("is_subcontracted"):
                        args["is_subcontracted"] = self.is_subcontracted

                    ret = get_item_details(args, self, for_validate=True, overwrite_warehouse=False)

                    for fieldname, value in ret.items():
                        if item.meta.get_field(fieldname) and value is not None:
                            if item.get(fieldname) is None or fieldname in force_item_fields:
                                if fieldname in ['item_tax_template','item_tax_rate'] and item.order_receiving_item and self.get("__islocal"):
                                    if frappe.get_value("Order Receiving Item", item.order_receiving_item, 'item_tax_template'):
                                        item.set(fieldname, value)
                                else:
                                    item.set(fieldname, value)

                            elif fieldname in ["cost_center", "conversion_factor"] and not item.get(fieldname):
                                item.set(fieldname, value)

                            elif fieldname == "serial_no":
                                # Ensure that serial numbers are matched against Stock UOM
                                item_conversion_factor = item.get("conversion_factor") or 1.0
                                item_qty = abs(item.get("qty")) * item_conversion_factor

                                if item_qty != len(get_serial_nos(item.get("serial_no"))):
                                    item.set(fieldname, value)

                            elif (
                                    ret.get("pricing_rule_removed")
                                    and value is not None
                                    and fieldname
                                    in [
                                        "discount_percentage",
                                        "discount_amount",
                                        "rate",
                                        "margin_rate_or_amount",
                                        "margin_type",
                                        "remove_free_item",
                                    ]
                            ):
                                # reset pricing rule fields if pricing_rule_removed
                                item.set(fieldname, value)

                    if self.doctype in ["Purchase Invoice", "Sales Invoice"] and item.meta.get_field(
                            "is_fixed_asset"
                    ):
                        item.set("is_fixed_asset", ret.get("is_fixed_asset", 0))

                    # Double check for cost center
                    # Items add via promotional scheme may not have cost center set
                    if hasattr(item, "cost_center") and not item.get("cost_center"):
                        item.set(
                            "cost_center", self.get("cost_center") or erpnext.get_default_cost_center(self.company)
                        )

                    if ret.get("pricing_rules"):
                        self.apply_pricing_rule_on_items(item, ret)
                        self.set_pricing_rule_details(item, ret)

            if self.doctype == "Purchase Invoice":
                self.set_expense_account(for_validate)


def update_p_r_c_tool_status(doc, method):
    if doc.purchase_invoice_creation_tool:
        prc_doc = frappe.get_doc("Purchase Invoice Creation Tool", doc.purchase_invoice_creation_tool)
        prc_doc.status = "Receipt Created"
        prc_doc.db_update()

def cancel_update_p_r_c_tool_status(doc, method):
    if doc.purchase_invoice_creation_tool:
        prc_doc = frappe.get_doc("Purchase Invoice Creation Tool", doc.purchase_invoice_creation_tool)
        prc_doc.status = "Success"
        prc_doc.db_update()

def update_md_status(doc, method):
    lst = []
    for res in doc.items:
        if res.material_demand_item and res.material_demand:
            if frappe.db.exists("Material Demand Item", res.material_demand_item):
                mdi = frappe.get_doc("Material Demand Item", res.material_demand_item)
                exit_qty = float(mdi.received_qty)
                mdi.received_qty = exit_qty + float(res.qty)
                mdi.db_update()

            if res.material_demand not in lst:
                lst.append(res.material_demand)

    for mrd in lst:
        md = frappe.get_doc("Material Demand", mrd)
        total_qty = 0
        for r in md.items:
            total_qty += r.received_qty
        per = round((total_qty / md.total_qty) * 100, 2)
        md.per_received = per
        if per < 99.99:
            md.status = "Partially Received"
        else:
            md.status = "Received"
        md.db_update()

def cancel_update_md_status(doc, method):
    lst = []
    for res in doc.items:
        if res.material_demand_item and res.material_demand:
            if frappe.db.exists("Material Demand Item", res.material_demand_item):
                mdi = frappe.get_doc("Material Demand Item", res.material_demand_item)
                exit_qty = float(mdi.received_qty)
                mdi.received_qty = exit_qty - float(res.qty)
                mdi.db_update()

            if res.material_demand not in lst:
                lst.append(res.material_demand)

    for mrd in lst:
        md = frappe.get_doc("Material Demand", mrd)
        total_qty = 0
        for r in md.items:
            total_qty += r.received_qty
        per = round((total_qty / md.total_qty) * 100, 2)
        md.per_received = per
        if per < 99.99:
            md.status = "Partially Received"
        else:
            md.status = "Received"
        md.db_update()


def calculate_item_level_tax_breakup(doc, method):
    if doc:
        itemised_tax, itemised_taxable_amount = get_itemised_tax_breakup_data(doc)
        if itemised_tax:
            for res in doc.items:
                total = 0
                if res.item_code in itemised_tax.keys():
                    for key in itemised_tax[res.item_code].keys():
                        if 'Sales Tax' in key:
                            res.sales_tax = flt(itemised_tax[res.item_code][key]['tax_amount']) if itemised_tax[res.item_code][key]['tax_amount'] else 0
                            total += flt(res.sales_tax)
                        if 'Further Tax' in key:
                            res.further_tax = flt(itemised_tax[res.item_code][key]['tax_amount']) if itemised_tax[res.item_code][key]['tax_amount'] else 0
                            total += flt(res.further_tax)
                        if 'Advance Tax' in key:
                            res.advance_tax = flt(itemised_tax[res.item_code][key]['tax_amount'])if itemised_tax[res.item_code][key]['tax_amount'] else 0
                res.total_includetaxes = flt(res.sales_tax + res.further_tax + res.advance_tax) + res.amount
        else:
            for res in doc.items:
                res.sales_tax = res.further_tax = res.advance_tax = res.total_includetaxes = 0

def calculate_line_level_tax(doc, method):
    for res in doc.items:
        if res.item_tax_template:
            item_tax_template = frappe.get_doc('Item Tax Template', res.item_tax_template)
            for tax in item_tax_template.taxes:
                if 'Sales Tax' in tax.tax_type:
                    res.sales_tax = res.amount * (tax.tax_rate / 100)
                if 'Further Tax' in tax.tax_type:
                        res.further_tax = res.amount * (tax.tax_rate / 100)
                if 'Advance Tax' in tax.tax_type:
                    res.advance_tax = res.amount * (tax.tax_rate / 100)
        res.total_includetaxes = flt(res.sales_tax + res.further_tax + res.advance_tax) + res.amount